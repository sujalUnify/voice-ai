import asyncio
import json
import logging

from openai import AsyncOpenAI

from app.config import MEMORY_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

logger = logging.getLogger(__name__)

DISTILL_PROMPT = """You are the memory curator for a voice assistant. Given one exchange
between the user and the assistant, extract durable facts worth remembering
(names, preferences, commitments, amounts, dates, decisions, unresolved
questions).

Rules:
- Skip small talk, greetings, filler, and anything trivially re-derivable.
- Each fact must be self-contained (no "he"/"she"/"it" without context).
- Rate importance 1-10 (10 = critical commitment or agreement, 1 = trivia).
- Return AT MOST 5 facts. Return [] if nothing is worth remembering.

Reply with ONLY a JSON array, no other text: [{"fact": "...", "importance": 7}]
"""

EVICT_PROMPT = """You are the memory curator for a voice assistant. The long-term memory
store is full. Given the entries (id, importance, fact), choose which
entries to DELETE to free slots. Prefer deleting: low importance, redundant
with another entry, outdated or superseded, or irrelevant to an ongoing
payment-collection conversation. Always keep commitments, amounts, names,
and agreements.

Reply with ONLY a JSON array of ids to delete, e.g. [3, 7]
"""


class MemoryCurator:
    """LLM-curated long-term memory via OpenRouter.

    Every call is timeout-guarded and failure-tolerant: memory is
    best-effort and must never break the conversation. These calls run in
    fire-and-forget background tasks — never on the hot latency path.
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
        self.model = MEMORY_MODEL

    async def _complete(self, user_content: str) -> str:
        response = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=400,
                temperature=0,
            ),
            timeout=8,
        )
        return (response.choices[0].message.content or "").strip()

    async def distill(self, exchange: dict) -> list[dict]:
        """Extract [{fact, importance}] from one {'user', 'ai'} exchange."""
        try:
            raw = await self._complete(
                DISTILL_PROMPT
                + "\nUSER: " + exchange["user"]
                + "\nASSISTANT: " + exchange["ai"]
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Memory distill failed (non-fatal): %s", e)
            return []
        return self._parse_facts(raw)

    @staticmethod
    def _parse_facts(raw: str) -> list[dict]:
        # models may wrap the array in prose or ``` fences; find the JSON
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end <= start:
            logger.warning("Memory distill returned no JSON array: %r", raw[:200])
            return []
        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            logger.warning("Memory distill returned unparseable JSON: %r", raw[:200])
            return []
        facts = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            fact = str(item.get("fact", "")).strip()
            try:
                importance = max(1, min(10, int(item.get("importance", 5))))
            except (TypeError, ValueError):
                importance = 5
            if fact:
                facts.append({"fact": fact, "importance": importance})
        return facts[:5]

    async def evict(self, entries: list[tuple[int, dict]], slots_needed: int) -> list[int]:
        """Given [(id, entry)], return ids of the least-important entries to delete."""
        if not entries or slots_needed <= 0:
            return []
        listing = "\n".join(
            f"id={eid} importance={e['importance']}: {e['fact']}"
            for eid, e in entries
        )
        try:
            raw = await self._complete(
                f"{EVICT_PROMPT}\n\nMemory entries:\n{listing}\n\n"
                f"Delete at least {slots_needed} entries."
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Memory evict failed (non-fatal): %s", e)
            return []
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end <= start:
            return []
        try:
            ids = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            logger.warning("Memory evict returned unparseable JSON: %r", raw[:200])
            return []
        valid = {eid for eid, _ in entries}
        return [i for i in ids if isinstance(i, int) and i in valid]
