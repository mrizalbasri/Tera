from langchain_core.callbacks import BaseCallbackHandler


class UsageCapture(BaseCallbackHandler):
    """Collect numeric provider usage, never prompts or response contents."""

    def __init__(self) -> None:
        self.usage: dict = {"status": "unavailable", "input_tokens": None, "output_tokens": None, "total_tokens": None}

    def on_llm_end(self, response, **kwargs) -> None:
        for generation in response.generations:
            for item in generation:
                metadata = getattr(getattr(item, "message", None), "usage_metadata", None)
                if not isinstance(metadata, dict):
                    continue
                values = {name: metadata.get(name) for name in ("input_tokens", "output_tokens", "total_tokens")}
                if all(isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10**12 for value in values.values()):
                    self.usage = {"status": "measured", **values}
