"""Only these classification codes may cross the retrieval audit boundary."""


class RetrievalError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
