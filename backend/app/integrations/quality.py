"""Deterministic receipt quality heuristics (no external OCR dependency)."""


class FileQualityChecker:
    """Scores basic readability signals from raw receipt bytes."""

    def check(self, content: bytes, *, media_type: str) -> tuple[float, list[str]]:
        findings: list[str] = []
        if media_type.startswith("image/") and len(content) < 100:
            findings.append("image_may_be_unreadable")
        if media_type == "application/pdf" and b"%%EOF" not in content:
            findings.append("pdf_metadata_incomplete")
        score = 0.5 if findings else 1.0
        return score, findings
