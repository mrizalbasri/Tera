"""In-memory file storage used by the memory backend and tests."""

from uuid import uuid4


class InMemoryFileStorage:
    """Stores receipt bytes under an opaque ``memory://`` reference."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def put(self, content: bytes, *, filename: str, media_type: str) -> str:
        reference = f"memory://{uuid4()}"
        self._files[reference] = content
        return reference

    def get(self, reference: str) -> bytes | None:
        return self._files.get(reference)

    def delete(self, reference: str) -> None:
        self._files.pop(reference, None)
