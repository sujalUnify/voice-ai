class LLMGenerationError(Exception):

    ERRORS = {
        1001: "Empty transcription or problem in transcription generation",
        1002: "LLM provider failed or problem in text generation",
        1003: "TTS failed or problem in voice generation",
    }

    def __init__(self, error_code: int, detail: str | None = None):
        self.error_code = error_code
        self.message = self.ERRORS.get(
            error_code,
            "Unknown LLM generation error"
        )
        self.detail = detail

        super().__init__(self.message)

    def __str__(self):
        if self.detail:
            return f"[LLM-{self.error_code}] {self.message}: {self.detail}"

        return f"[LLM-{self.error_code}] {self.message}"