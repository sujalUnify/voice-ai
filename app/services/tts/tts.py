import asyncio
import contextlib
import logging
import struct
import time

import aiohttp

from app.config import (
    GROQ_API_KEY,
    OPENROUTER_API_KEY,
    TTS_FALLBACK_MODEL,
    TTS_FALLBACK_PROVIDER,
    TTS_FALLBACK_VOICE,
    TTS_KEEPALIVE_URL,
    TTS_MODEL,
    TTS_PROVIDER,
    TTS_SAMPLE_RATE,
    TTS_VOICE,
)
from app.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/audio/speech",
        "keepalive": "https://api.groq.com/openai/v1/models",
        "wire_format": "wav",  # streams RIFF; header stripped on receipt
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/audio/speech",
        "keepalive": "https://openrouter.ai/api/v1/models",
        "wire_format": "pcm",
    },
}


def _provider_config(provider: str, model: str, voice: str) -> dict:
    base = _PROVIDERS[provider]
    key = GROQ_API_KEY if provider == "groq" else OPENROUTER_API_KEY
    return {
        "name": provider,
        "url": base["url"],
        "keepalive": base["keepalive"],
        "wire_format": base["wire_format"],
        "api_key": key,
        "model": model,
        "voice": voice,
    }


class TextToSpeech:
    """Streams 16-bit LE mono PCM (TTS_SAMPLE_RATE) for text fragments.

    The aiohttp session is process-wide and kept warm by a background
    pinger, so every fragment request reuses an established TCP+TLS
    connection instead of paying DNS + handshake (~100-300 ms) again.

    If the primary gateway fails (e.g. Groq Orpheus free tier: 100
    requests/day), fragments fall back to the configured second gateway.
    """

    _session: aiohttp.ClientSession | None = None
    _keeper: asyncio.Task | None = None

    @classmethod
    async def session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60, connect=8),
                connector=aiohttp.TCPConnector(
                    limit=16,
                    keepalive_timeout=75,
                    ttl_dns_cache=600,
                ),
            )
            cls._keeper = asyncio.create_task(cls._keep_warm())
        return cls._session

    @classmethod
    async def _keep_warm(cls):
        """Ping every 20 s so the pooled connection never goes stale."""
        while True:
            await asyncio.sleep(20)
            session = cls._session
            if session is None or session.closed:
                return
            with contextlib.suppress(Exception):
                async with session.head(TTS_KEEPALIVE_URL) as r:
                    await r.read()

    def __init__(self):
        self.primary = _provider_config(TTS_PROVIDER, TTS_MODEL, TTS_VOICE)
        self.fallback = None
        if TTS_FALLBACK_PROVIDER:
            self.fallback = _provider_config(
                TTS_FALLBACK_PROVIDER, TTS_FALLBACK_MODEL, TTS_FALLBACK_VOICE
            )
        self._keepalive_url = self.primary["keepalive"]
        self._primary_blocked_until = 0.0  # monotonic ts; skip primary while set

    async def warm_up(self):
        with contextlib.suppress(Exception):
            await TextToSpeech.session()

    async def audio_generation(self, text: str):
        """Yields raw PCM chunks as they arrive from the provider."""
        try:
            if time.monotonic() < self._primary_blocked_until:
                async for chunk in self._stream(self.fallback, text):
                    yield chunk
                return
            async for chunk in self._stream(self.primary, text):
                yield chunk
        except asyncio.CancelledError:
            raise
        except LLMGenerationError as e:
            if self.fallback is None:
                raise
            # primary is down / rate-limited: use the fallback for this
            # fragment and skip the primary entirely for a grace period
            if "TTS HTTP 429" in str(e) or "TTS HTTP 5" in str(e):
                self._primary_blocked_until = time.monotonic() + 60
            logger.warning("TTS %s failed (%s) — falling back to %s",
                           self.primary["name"], str(e)[:120], self.fallback["name"])
            async for chunk in self._stream(self.fallback, text):
                yield chunk

    @staticmethod
    def _payload(provider: dict, text: str) -> dict:
        payload = {
            "model": provider["model"],
            "input": text,
            "response_format": "pcm" if provider["wire_format"] == "pcm" else "wav",
        }
        if provider["voice"]:
            payload["voice"] = provider["voice"]
        return payload

    async def _stream(self, provider: dict, text: str):
        try:
            session = await TextToSpeech.session()
            resp = await session.post(
                provider["url"],
                headers={
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                },
                json=self._payload(provider, text),
            )
            try:
                if resp.status != 200:
                    detail = (await resp.text())[:300]
                    raise LLMGenerationError(1003, detail=f"TTS HTTP {resp.status}: {detail}")

                if provider["wire_format"] == "wav":
                    # streamed WAV: parse the RIFF header once, then forward
                    # the payload as raw PCM
                    first = await self._strip_wav_header(resp)
                    if first:
                        yield first
                async for chunk in resp.content.iter_any():
                    if chunk:
                        yield chunk
            finally:
                resp.release()

        except asyncio.CancelledError:
            logger.info("TTS generation cancelled")
            raise
        except LLMGenerationError:
            raise
        except Exception as e:
            logger.exception("TTS request failed")
            raise LLMGenerationError(1003, detail=str(e)) from e

    @staticmethod
    async def _strip_wav_header(resp: aiohttp.ClientResponse) -> bytes:
        """Consume the RIFF header of the streaming WAV, return first PCM bytes."""
        buf = b""
        while True:
            pos = 12  # skip 'RIFF' + size + 'WAVE'
            while pos + 8 <= len(buf):
                chunk_id = buf[pos:pos + 4]
                (size,) = struct.unpack("<I", buf[pos + 4:pos + 8])
                if chunk_id == b"data":
                    pcm = buf[pos + 8:]
                    # sanity: report actual rate if it ever differs from config
                    if len(buf) >= 36:
                        (rate,) = struct.unpack("<I", buf[24:28])
                        if rate != TTS_SAMPLE_RATE:
                            logger.warning("TTS WAV rate %d != configured %d", rate, TTS_SAMPLE_RATE)
                    return pcm
                pos += 8 + size + (size & 1)
            chunk = await resp.content.read(256)
            if not chunk:
                raise LLMGenerationError(1003, detail="TTS WAV stream ended before data chunk")
            buf += chunk