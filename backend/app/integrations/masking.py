"""Sensitive data masking before any external provider call (FR-13).

Deterministic, pattern-based masking: the same value always maps to the same
token (stable HMAC prefix), so provider responses can be correlated back to
the original without ever sending the raw value across the boundary. The
token mapping lives in-process only and never enters audit payloads or logs.
"""

import hashlib
import hmac
import re
from dataclasses import dataclass, field

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Indonesian and general phone formats: +62..., 08xx, with separators.
_PHONE = re.compile(r"(?:\+62|62|0)8\d{1,13}[\d\s.-]{0,8}")
# 10-19 digit runs that look like card/account numbers (not amounts).
_LONG_DIGITS = re.compile(r"\b\d{10,19}\b")

_TOKEN_TEMPLATE = "[MASKED:{kind}:{token}]"


@dataclass(frozen=True)
class MaskingResult:
    """Masked payload plus safe metadata — never the reverse mapping."""

    masked_text: str
    correlation_reference: str
    masked_kinds: tuple[str, ...] = ()
    masked_count: int = 0


class SensitiveDataMasker:
    """Classify and redact sensitive values with deterministic tokens."""

    version = "masker-v1"

    def __init__(self, secret: str = "expense-agent-masking") -> None:
        self._secret = secret.encode()

    def mask(self, value: object) -> MaskingResult:
        text = "" if value is None else str(value)
        kinds: list[str] = []
        count = 0

        def _token(kind: str, raw: str) -> str:
            digest = hmac.new(self._secret, raw.encode(), hashlib.sha256)
            return _TOKEN_TEMPLATE.format(kind=kind, token=digest.hexdigest()[:10])

        def _replace(pattern: re.Pattern[str], kind: str) -> None:
            nonlocal text, count
            matches = pattern.findall(text)
            if matches:
                kinds.append(kind)
                count += len(matches)
                text = pattern.sub(lambda m: _token(kind, m.group(0)), text)

        _replace(_EMAIL, "email")
        _replace(_PHONE, "phone")
        _replace(_LONG_DIGITS, "account")

        correlation = hmac.new(
            self._secret, ("" if value is None else str(value)).encode(), hashlib.sha256
        ).hexdigest()[:16]
        return MaskingResult(
            masked_text=text,
            correlation_reference=f"corr_{correlation}",
            masked_kinds=tuple(sorted(set(kinds))),
            masked_count=count,
        )

    def mask_mapping(self, payload: dict[str, object]) -> dict[str, object]:
        """Mask every string value in a flat mapping."""
        return {
            key: self.mask(value).masked_text if isinstance(value, str) else value
            for key, value in payload.items()
        }
