Title: OpenRouter Text-to-Speech - Complete Documentation

URL Source: https://openrouter.ai/docs/guides/overview/multimodal/tts

Markdown Content:
OpenRouter supports text-to-speech (TTS) via a dedicated `/api/v1/audio/speech` endpoint that is compatible with the [OpenAI Audio Speech API](https://platform.openai.com/docs/api-reference/audio/createSpeech). Send text and receive a raw audio byte stream in your chosen format.

## Model Discovery

You can find TTS models in several ways:

### Via the API

Use the `output_modalities` query parameter on the [Models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties) to discover TTS models:

### On the Models Page

Visit the [Models page](https://openrouter.ai/docs/guides/overview/models) and filter by output modalities to find models capable of speech synthesis. Look for models that list `"speech"` in their output modalities.

## API Usage

Send a `POST` request to `/api/v1/audio/speech` with the text you want to synthesize. The response is a raw audio byte stream (not JSON), so you can pipe it directly to a file or audio player.

### Basic Example

### Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `model` | string | Yes | The TTS model to use (e.g., `openai/gpt-4o-mini-tts-2025-12-15`, `mistralai/voxtral-mini-tts-2603`) |
| `input` | string | Yes | The text to synthesize into speech. Some models treat it as a prompt that can also describe non-speech audio; see [Non-Speech Prompts](https://openrouter.ai/docs/guides/overview/multimodal/tts#non-speech-prompts) below |
| `voice` | string | Provider-dependent | Voice identifier. Available voices vary by model, so check each model’s page on the [Models page](https://openrouter.ai/docs/guides/overview/models) for supported voices. Omit this parameter only when the selected provider documents a default voice; otherwise an explicit voice is required. |
| `response_format` | string | No | Audio output format: `mp3` or `pcm`. Defaults to `pcm` |
| `speed` | number | No | Playback speed multiplier. Honored by models that support it (e.g., OpenAI TTS). Other providers either ignore it or return a 400 for a non-default value when the model has no speed control. Defaults to `1.0` |
| `input_references` | array | No | Reference content for stateless voice cloning or voice design: one to three `input_audio` parts (each optionally paired with a `text` transcript), or exactly one `image_url` part. See [Voice Cloning](https://openrouter.ai/docs/guides/overview/multimodal/tts#voice-cloning) below |
| `provider` | object | No | Data policy routing preferences (`zdr`, `data_collection`) and provider-specific passthrough options under `provider.options`. With `zdr: true`, the request only routes to [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr) endpoints. Other routing preferences (`order`, `only`, `ignore`) are not applied to speech requests |

When `voice` is omitted, OpenRouter only forwards the request to providers whose adapter supports a provider-side default voice. For other providers, the request is rejected with a validation error.

### Voice Cloning

Some models support **stateless voice cloning**: you send a short sample of reference audio directly with the TTS request, and the generated speech mimics that voice. No separate voice-creation or upload step is required.Pass the reference audio as a base64 `input_audio` part in `input_references` (a `data:audio/...;base64,` URI also works), and optionally include its transcript as a `text` part:

Instead of inline base64, `input_audio` can carry a public `url`. OpenRouter downloads the file and forwards the bytes to the provider; the provider never receives your URL:

Not every provider of a voice-cloning model supports voice cloning, and only some accept more than one clip or an image reference. Requests that carry references are only routed to endpoints whose capability flags allow them. Check these fields on the [endpoints API](https://openrouter.ai/docs/docs/api-reference/list-endpoints-for-a-model):

| Field | Meaning |
| --- | --- |
| `supports_voice_cloning` | The endpoint accepts `input_audio` reference clips |
| `supports_multiple_audio_references` | The endpoint accepts more than one `input_audio` clip per request |
| `supports_image_reference` | The endpoint accepts an `image_url` reference |

#### Multiple Reference Clips

Models such as [Seed Audio 1.0](https://openrouter.ai/bytedance-seed/seed-audio-1-0) accept up to three `input_audio` clips in one request, so a single generation can switch between voices. Clips are numbered in the order you send them, and you address them from `input` with the placeholders `@Audio1`, `@Audio2`, and `@Audio3`. If you also send transcripts with more than one clip, place each clip’s `text` part immediately after the clip it describes:

Placeholder rules, as enforced by Seed Audio 1.0 (currently the only model that accepts more than one clip; a model that accepts a single clip takes `input` verbatim and does not validate placeholders):

*   With a single clip, the placeholder is optional: the whole input is spoken in that voice. If you include one, it must be `@Audio1`.
*   With more than one clip, every clip must be referenced at least once. A request that supplies two clips but never mentions `@Audio2` is rejected with a 400.
*   A placeholder that points at a clip you did not send (for example `@Audio3` with two clips) is rejected with a 400, as is a placeholder in a request with no audio references.
*   Transcripts are optional and provider-dependent: Fish Audio sends each clip’s transcript to the model, while Seed Audio 1.0 ignores them. With a single clip the `text` part may appear before or after it; with multiple clips a `text` part must immediately follow its clip, and a transcript with no preceding clip is rejected.

#### Image References

Some models can design a voice from a picture instead of an audio sample. Send exactly one `image_url` part, either as a base64 data URI or as a public `http(s)` URL that OpenRouter downloads and forwards as bytes. JPEG, PNG, and WebP are accepted:

Audio and image references cannot be combined in one request, and `@AudioN` placeholders are rejected when no audio clip is present.

#### Limits and Requirements

*   Supported audio formats for reference clips are provider-specific.
*   `input_references` accepts one to three `input_audio` parts (each optionally paired with a `text` transcript) or exactly one `image_url` part, never both kinds in the same request. An empty array is treated as no reference.
*   Each inline reference is limited to 20 MiB of base64 (15 MiB of decoded media); a larger `data` value is rejected with a 400. Remote downloads are capped at the same 15 MiB and a larger file is rejected with a 413.
*   Remote `url` values must be public `http(s)` URLs of at most 2048 characters. OpenRouter fetches them server-side and forwards only the bytes, never the URL.
*   A `text` transcript is limited to 10,000 characters.
*   Seed Audio 1.0 treats both `voice` (a Seed speaker ID) and `input_references` as the reference voice, so a request that sends both is rejected with a 400. Use one or the other.

When Seed Audio 1.0 rejects a reference or prompt for reasons of its own, such as a clip it cannot decode, OpenRouter returns a 400 whose message begins with `Provider rejected the request:` followed by the provider’s explanation, with any base64 payload redacted. Other provider failures are reported with OpenRouter’s own messages.

### Non-Speech Prompts

For most TTS models, `input` is read aloud verbatim. Seed Audio 1.0 instead treats `input` as a prompt that is forwarded unchanged to the model, so it can describe the delivery of the speech, or describe sound that is not speech at all: sound effects, ambience, or a scene. Omit `voice` and `input_references` when you want the model to infer everything from the prompt:

Seed Audio 1.0 caps generated audio at 120 seconds per request; see [Seed Audio 1.0](https://openrouter.ai/docs/guides/overview/multimodal/tts#seed-audio-10) below for its other limits.

### Provider-Specific Options

You can pass provider-specific options using the `provider` parameter. Options are keyed by provider slug, and only the options for the matched provider are forwarded:

#### Seed Audio 1.0

Seed Audio 1.0 takes no provider options; every field it reads is derived from the standard parameters. It enforces these limits with a 400:

*   `input` is limited to 3000 characters.
*   `speed` must be between 0.5 and 2.0.
*   Generated audio is capped at 120 seconds per request. A prompt that would produce more than that is rejected before any audio is returned.

#### Azure (MAI-Voice)

Azure serves `microsoft/mai-voice-2`, `microsoft/mai-voice-2.1`, and `microsoft/mai-voice-2.1-flash`. Azure TTS uses SSML internally, but this is fully abstracted, so you only need the standard parameters. The `voice` parameter takes a full Azure voice ID with the model suffix (`:MAI-Voice-2`, `:MAI-Voice-2.1`, or `:MAI-Voice-2.1-Flash`, e.g., `en-US-Harper:MAI-Voice-2.1`), and the voice’s locale sets the synthesis language. Set `response_format` to `mp3` or `pcm` (24 kHz mono). The full list of voices for each model is in the `supported_voices` field of the [models API](https://openrouter.ai/api/v1/models?output_modalities=speech).

#### Google (Gemini TTS)

Gemini 3.8 TTS models read `input` verbatim, so delivery directions written into the text may be spoken aloud. Pass the style as `speech_metadata` in provider options instead. It is attached to the input text part of the upstream request, and any other options are forwarded as generation config:

| Option | Type | Description |
| --- | --- | --- |
| `speech_metadata.style` | string | Sustained delivery style for the input (e.g., `cheerful and friendly`, `whispering`). |

## Response Format

The TTS endpoint returns a **raw audio byte stream**, not JSON. The response includes the following headers:

| Header | Description |
| --- | --- |
| `Content-Type` | The MIME type of the audio. `audio/mpeg` for `mp3` format, `audio/pcm` for `pcm` format |
| `X-Generation-Id` | The unique generation ID for the request, useful for tracking and debugging |

### Output Formats

| Format | Content-Type | Description |
| --- | --- | --- |
| `mp3` | `audio/mpeg` | Compressed audio, smaller file size. Good for storage and playback |
| `pcm` | `audio/pcm` | Uncompressed raw audio. Lower latency, suitable for real-time streaming pipelines |

## Pricing

Most TTS models are priced **per character** of input text. Some audio generation models, such as Seed Audio 1.0, are priced **per second** of generated audio instead. Pricing varies by model and provider. You can check the per-character or per-second cost for each model on the [Models page](https://openrouter.ai/docs/guides/overview/models) or via the [Models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties), where per-second models report their rate under `pricing.completion`.

## OpenAI SDK Compatibility

The TTS endpoint is fully compatible with the OpenAI SDK. You can use the OpenAI client libraries by pointing them at OpenRouter’s base URL:

## Best Practices

*   **Choose the right format**: Use `mp3` for storage and general playback. Use `pcm` for real-time streaming pipelines where latency matters
*   **Voice selection**: Different providers offer different voices. Check the model’s documentation or experiment with available voices to find the best fit for your use case
*   **Input length**: For very long texts, consider splitting the input into smaller segments and concatenating the audio output. This can improve reliability and reduce latency for the first audio chunk
*   **Speed parameter**: The `speed` parameter is only supported by certain providers (e.g., OpenAI). Providers that don’t support it either ignore it or reject a non-default value with a 400 when the model has no speed control, so omit it unless the model documents speed

## Troubleshooting

**Empty or corrupted audio file?**

*   Verify the `response_format` matches how you’re saving the file (e.g., don’t save `pcm` output with a `.mp3` extension)
*   Check the response status code, since non-200 responses return JSON error bodies, not audio

**Model not found?**

*   Use the [Models page](https://openrouter.ai/docs/guides/overview/models) to find available TTS models
*   Verify the model slug is correct (e.g., `openai/gpt-4o-mini-tts-2025-12-15`, not `gpt-4o-mini-tts`)

**Voice not available?**

*   Available voices vary by provider. Check the provider’s documentation for supported voice identifiers
*   Each model has its own set of voices, so check the model’s page on the [Models page](https://openrouter.ai/docs/guides/overview/models) for the full list
