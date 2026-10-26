Title: Create speech - OpenRouter | Documentation

URL Source: https://openrouter.ai/docs/api/api-reference/tts/create-speech

Markdown Content:
> ## Documentation Index
> 
> 
> Fetch the complete documentation index at: [/docs/llms.txt](https://openrouter.ai/docs/llms.txt)
> 
> 
> Use this file to discover all available pages before exploring further.

[Skip to main content](https://openrouter.ai/docs/api/api-reference/tts/create-speech#content-area)

[OpenRouter | Documentation home page![Image 1: light logo](https://mintcdn.com/openrouter-d02e98a0/ksNSeB_K7gD-BUDh/assets/logo-v2-light.svg?fit=max&auto=format&n=ksNSeB_K7gD-BUDh&q=85&s=690e45873843519efe02bcbe45795dac)![Image 2: dark logo](https://mintcdn.com/openrouter-d02e98a0/ksNSeB_K7gD-BUDh/assets/logo-v2-dark.svg?fit=max&auto=format&n=ksNSeB_K7gD-BUDh&q=85&s=8ba2f49b11cd9839c37dd03c62537ebd)](https://openrouter.ai/)

Search...

Ctrl K Ask Assistant CTRLI

*   [Models](https://openrouter.ai/models)
*   [Benchmarks](https://openrouter.ai/benchmarks)
*   [Chat](https://openrouter.ai/chat)
*   [Rankings](https://openrouter.ai/rankings)
*   [Apps](https://openrouter.ai/apps)
*   [Ori](https://openrouter.ai/ori)
*   [Pricing](https://openrouter.ai/pricing)
*   [Sign In](https://openrouter.ai/sign-in)
*   [Sign In](https://openrouter.ai/sign-in?redirect_url=https%3A%2F%2Fopenrouter.ai%2Fdocs%2Fapi%2Fapi-reference%2Ftts%2Fcreate-speech)

Search...

Navigation

TTS

Create speech

[Docs](https://openrouter.ai/docs/quickstart)[API Reference](https://openrouter.ai/docs/api_reference/overview)[Client SDKs](https://openrouter.ai/docs/client-sdks/overview)[Agent SDK](https://openrouter.ai/docs/agent-sdk/overview)[Cookbook](https://openrouter.ai/docs/cookbook/get-started/quickstart)

### API Guides

*   [Overview](https://openrouter.ai/docs/api_reference/overview)
*   [Streaming](https://openrouter.ai/docs/api_reference/streaming)
*   [Embeddings](https://openrouter.ai/docs/api_reference/embeddings)
*   [Limits](https://openrouter.ai/docs/api_reference/limits)
*   [Authentication](https://openrouter.ai/docs/api_reference/authentication)
*   [Parameters](https://openrouter.ai/docs/api_reference/parameters)
*   [Errors and Debugging](https://openrouter.ai/docs/api_reference/errors-and-debugging)
*    Responses API  

### Versioning

*   [API Versioning](https://openrouter.ai/docs/api_reference/versioning)
*   [API Changelog](https://openrouter.ai/docs/changelog)

### API Reference

*   Analytics  
*   alpha.decisions  
*   TTS  
    *   [POST Create speech](https://openrouter.ai/docs/api/api-reference/tts/create-speech)

*   STT  
*   OAuth  
*   Batch  
*   Benchmarks  
*   BYOK  
*   Chat  
*   Classifications  
*   Containers  
*   Credits  
*   Datasets  
*   Embeddings  
*   End Users  
*   Endpoints  
*   Files  
*   Generations  
*   Guardrails  
*   Images  
*   Interns  
*   API Keys  
*   Anthropic Messages  
*   Models  
*   Observability  
*   Organization  
*   Presets  
*   Private Endpoints  
*   Providers  
*   Rerank  
*   Responses  
*   SCIM  
*   SystemOne  
*   Tools  
*   Vault  
*   Video Generation  
*   Workspaces  

Create speech

cURL

```
curl --request POST \
  --url https://openrouter.ai/api/v1/audio/speech \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json' \
  --data '
{
  "input": "Hello world",
  "model": "mistralai/voxtral-mini-tts-2603",
  "response_format": "pcm",
  "speed": 1,
  "voice": "en_paul_neutral"
}
'
```

```
import requests

url = "https://openrouter.ai/api/v1/audio/speech"

payload = {
    "input": "Hello world",
    "model": "mistralai/voxtral-mini-tts-2603",
    "response_format": "pcm",
    "speed": 1,
    "voice": "en_paul_neutral"
}
headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)
```

```
const options = {
  method: 'POST',
  headers: {Authorization: 'Bearer <token>', 'Content-Type': 'application/json'},
  body: JSON.stringify({
    input: 'Hello world',
    model: 'mistralai/voxtral-mini-tts-2603',
    response_format: 'pcm',
    speed: 1,
    voice: 'en_paul_neutral'
  })
};

fetch('https://openrouter.ai/api/v1/audio/speech', options)
  .then(res => res.json())
  .then(res => console.log(res))
  .catch(err => console.error(err));
```

```
<?php

$curl = curl_init();

curl_setopt_array($curl, [
  CURLOPT_URL => "https://openrouter.ai/api/v1/audio/speech",
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_ENCODING => "",
  CURLOPT_MAXREDIRS => 10,
  CURLOPT_TIMEOUT => 30,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => "POST",
  CURLOPT_POSTFIELDS => json_encode([
    'input' => 'Hello world',
    'model' => 'mistralai/voxtral-mini-tts-2603',
    'response_format' => 'pcm',
    'speed' => 1,
    'voice' => 'en_paul_neutral'
  ]),
  CURLOPT_HTTPHEADER => [
    "Authorization: Bearer <token>",
    "Content-Type: application/json"
  ],
]);

$response = curl_exec($curl);
$err = curl_error($curl);

curl_close($curl);

if ($err) {
  echo "cURL Error #:" . $err;
} else {
  echo $response;
}
```

```
package main

import (
	"fmt"
	"strings"
	"net/http"
	"io"
)

func main() {

	url := "https://openrouter.ai/api/v1/audio/speech"

	payload := strings.NewReader("{\n  \"input\": \"Hello world\",\n  \"model\": \"mistralai/voxtral-mini-tts-2603\",\n  \"response_format\": \"pcm\",\n  \"speed\": 1,\n  \"voice\": \"en_paul_neutral\"\n}")

	req, _ := http.NewRequest("POST", url, payload)

	req.Header.Add("Authorization", "Bearer <token>")
	req.Header.Add("Content-Type", "application/json")

	res, _ := http.DefaultClient.Do(req)

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(string(body))

}
```

```
HttpResponse<String> response = Unirest.post("https://openrouter.ai/api/v1/audio/speech")
  .header("Authorization", "Bearer <token>")
  .header("Content-Type", "application/json")
  .body("{\n  \"input\": \"Hello world\",\n  \"model\": \"mistralai/voxtral-mini-tts-2603\",\n  \"response_format\": \"pcm\",\n  \"speed\": 1,\n  \"voice\": \"en_paul_neutral\"\n}")
  .asString();
```

```
require 'uri'
require 'net/http'

url = URI("https://openrouter.ai/api/v1/audio/speech")

http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true

request = Net::HTTP::Post.new(url)
request["Authorization"] = 'Bearer <token>'
request["Content-Type"] = 'application/json'
request.body = "{\n  \"input\": \"Hello world\",\n  \"model\": \"mistralai/voxtral-mini-tts-2603\",\n  \"response_format\": \"pcm\",\n  \"speed\": 1,\n  \"voice\": \"en_paul_neutral\"\n}"

response = http.request(request)
puts response.read_body
```

200

400

401

402

403

404

413

429

500

502

503

524

529

`"<binary audio data>"`

```
{
  "error": {
    "code": 400,
    "message": "Invalid request parameters"
  }
}
```

```
{
  "error": {
    "code": 401,
    "message": "Missing Authentication header"
  }
}
```

```
{
  "error": {
    "code": 402,
    "message": "Insufficient credits. Add more using https://openrouter.ai/credits"
  }
}
```

```
{
  "error": {
    "code": 403,
    "message": "Only management keys can perform this operation"
  }
}
```

```
{
  "error": {
    "code": 404,
    "message": "Resource not found"
  }
}
```

```
{
  "error": {
    "code": 413,
    "message": "Request payload too large"
  }
}
```

```
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded"
  }
}
```

```
{
  "error": {
    "code": 500,
    "message": "Internal Server Error"
  }
}
```

```
{
  "error": {
    "code": 502,
    "message": "Provider returned error"
  }
}
```

```
{
  "error": {
    "code": 503,
    "message": "Service temporarily unavailable"
  }
}
```

```
{
  "error": {
    "code": 524,
    "message": "Request timed out. Please try again later."
  }
}
```

```
{
  "error": {
    "code": 529,
    "message": "Provider returned error"
  }
}
```

TTS

# Create speech

Copy page Copy page

Synthesizes audio from the input text. Returns a raw audio bytestream in the requested format (e.g. mp3, pcm, wav).

Copy page Copy page

POST

/

audio

/

speech

Try it

Create speech

cURL

```
curl --request POST \
  --url https://openrouter.ai/api/v1/audio/speech \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json' \
  --data '
{
  "input": "Hello world",
  "model": "mistralai/voxtral-mini-tts-2603",
  "response_format": "pcm",
  "speed": 1,
  "voice": "en_paul_neutral"
}
'
```

```
import requests

url = "https://openrouter.ai/api/v1/audio/speech"

payload = {
    "input": "Hello world",
    "model": "mistralai/voxtral-mini-tts-2603",
    "response_format": "pcm",
    "speed": 1,
    "voice": "en_paul_neutral"
}
headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)
```

```
const options = {
  method: 'POST',
  headers: {Authorization: 'Bearer <token>', 'Content-Type': 'application/json'},
  body: JSON.stringify({
    input: 'Hello world',
    model: 'mistralai/voxtral-mini-tts-2603',
    response_format: 'pcm',
    speed: 1,
    voice: 'en_paul_neutral'
  })
};

fetch('https://openrouter.ai/api/v1/audio/speech', options)
  .then(res => res.json())
  .then(res => console.log(res))
  .catch(err => console.error(err));
```

```
<?php

$curl = curl_init();

curl_setopt_array($curl, [
  CURLOPT_URL => "https://openrouter.ai/api/v1/audio/speech",
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_ENCODING => "",
  CURLOPT_MAXREDIRS => 10,
  CURLOPT_TIMEOUT => 30,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => "POST",
  CURLOPT_POSTFIELDS => json_encode([
    'input' => 'Hello world',
    'model' => 'mistralai/voxtral-mini-tts-2603',
    'response_format' => 'pcm',
    'speed' => 1,
    'voice' => 'en_paul_neutral'
  ]),
  CURLOPT_HTTPHEADER => [
    "Authorization: Bearer <token>",
    "Content-Type: application/json"
  ],
]);

$response = curl_exec($curl);
$err = curl_error($curl);

curl_close($curl);

if ($err) {
  echo "cURL Error #:" . $err;
} else {
  echo $response;
}
```

```
package main

import (
	"fmt"
	"strings"
	"net/http"
	"io"
)

func main() {

	url := "https://openrouter.ai/api/v1/audio/speech"

	payload := strings.NewReader("{\n  \"input\": \"Hello world\",\n  \"model\": \"mistralai/voxtral-mini-tts-2603\",\n  \"response_format\": \"pcm\",\n  \"speed\": 1,\n  \"voice\": \"en_paul_neutral\"\n}")

	req, _ := http.NewRequest("POST", url, payload)

	req.Header.Add("Authorization", "Bearer <token>")
	req.Header.Add("Content-Type", "application/json")

	res, _ := http.DefaultClient.Do(req)

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(string(body))

}
```

```
HttpResponse<String> response = Unirest.post("https://openrouter.ai/api/v1/audio/speech")
  .header("Authorization", "Bearer <token>")
  .header("Content-Type", "application/json")
  .body("{\n  \"input\": \"Hello world\",\n  \"model\": \"mistralai/voxtral-mini-tts-2603\",\n  \"response_format\": \"pcm\",\n  \"speed\": 1,\n  \"voice\": \"en_paul_neutral\"\n}")
  .asString();
```

```
require 'uri'
require 'net/http'

url = URI("https://openrouter.ai/api/v1/audio/speech")

http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true

request = Net::HTTP::Post.new(url)
request["Authorization"] = 'Bearer <token>'
request["Content-Type"] = 'application/json'
request.body = "{\n  \"input\": \"Hello world\",\n  \"model\": \"mistralai/voxtral-mini-tts-2603\",\n  \"response_format\": \"pcm\",\n  \"speed\": 1,\n  \"voice\": \"en_paul_neutral\"\n}"

response = http.request(request)
puts response.read_body
```

200

400

401

402

403

404

413

429

500

502

503

524

529

`"<binary audio data>"`

```
{
  "error": {
    "code": 400,
    "message": "Invalid request parameters"
  }
}
```

```
{
  "error": {
    "code": 401,
    "message": "Missing Authentication header"
  }
}
```

```
{
  "error": {
    "code": 402,
    "message": "Insufficient credits. Add more using https://openrouter.ai/credits"
  }
}
```

```
{
  "error": {
    "code": 403,
    "message": "Only management keys can perform this operation"
  }
}
```

```
{
  "error": {
    "code": 404,
    "message": "Resource not found"
  }
}
```

```
{
  "error": {
    "code": 413,
    "message": "Request payload too large"
  }
}
```

```
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded"
  }
}
```

```
{
  "error": {
    "code": 500,
    "message": "Internal Server Error"
  }
}
```

```
{
  "error": {
    "code": 502,
    "message": "Provider returned error"
  }
}
```

```
{
  "error": {
    "code": 503,
    "message": "Service temporarily unavailable"
  }
}
```

```
{
  "error": {
    "code": 524,
    "message": "Request timed out. Please try again later."
  }
}
```

```
{
  "error": {
    "code": 529,
    "message": "Provider returned error"
  }
}
```

#### Authorizations

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#authorization-authorization)

Authorization

string

header

required

API key as bearer token in Authorization header

#### Body

application/json

Text-to-speech request input

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-input)

input

string

required

Text to synthesize

Example:

`"Hello world"`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-model)

model

string

required

TTS model identifier

Example:

`"mistralai/voxtral-mini-tts-2603"`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-input-references)

input_references

object[]

Reference content for stateless voice cloning or voice design. Audio mode: one to three `input_audio` parts, each optionally paired with a `text` part carrying its transcript (a single clip accepts its transcript before or after it; with multiple clips each transcript immediately follows its clip); only routed to endpoints that support voice cloning (and multiple references when more than one part is sent). Image mode: exactly one `image_url` part; only routed to endpoints that support image references. The two modes cannot be mixed. An empty array is treated as no reference.

Reference content part for stateless voice cloning or voice design

*   Option 1 
*   Option 2 
*   Option 3 

Show child attributes

Example:

`{  "input_audio": {    "data": "data:audio/wav;base64,UklGRuQXDABXQVZF..."  },  "type": "input_audio"}`

Example:

`[  {    "input_audio": {      "data": "data:audio/wav;base64,UklGRuQXDABXQVZF..."    },    "type": "input_audio"  },  {    "text": "I used to rule the world.",    "type": "text"  }]`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-provider)

provider

object

Provider configuration: data policy routing preferences (`zdr`, `data_collection`) and provider-specific passthrough options

Show child attributes

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-response-format)

response_format

enum<string>

default:pcm

Audio output format

Available options: 

`mp3`, 

`pcm`

Example:

`"pcm"`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-session-id)

session_id

string

A unique identifier for grouping related requests (e.g., a conversation or agent workflow). Used for observability grouping in Broadcast and private logging; never sent to the provider. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 256 characters.

Maximum string length: `256`

Example:

`"session-1234"`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-speed)

speed

number<double>

Playback speed multiplier. Honored by models that support it (e.g. OpenAI TTS). Other providers either ignore it or return a 400 for a non-default value when the model has no speed control.

Example:

`1`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-trace)

trace

object

Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.

Show child attributes

Example:

`{  "trace_id": "trace-abc123",  "trace_name": "my-app-trace"}`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-user)

user

string

A unique identifier representing your end-user. Forwarded to Broadcast and private logging as the end-user id; never sent to the provider.

Maximum string length: `256`

Example:

`"user-1234"`

[​](https://openrouter.ai/docs/api/api-reference/tts/create-speech#body-voice)

voice

string

Voice identifier (provider-specific).

Minimum string length: `1`

Example:

`"en_paul_neutral"`

#### Response

200

audio/*

Audio bytes stream

Raw audio bytestream. Content-Type varies by requested format (audio/mpeg for mp3, audio/pcm for pcm — 16-bit little-endian).

[Submit a Decisions request](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request)[Create transcription](https://openrouter.ai/docs/api/api-reference/stt/create-transcription)

Assistant

Responses are generated using AI and may contain mistakes.
