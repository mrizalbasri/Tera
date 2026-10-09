"""Queries contain canonical policy concepts, never arbitrary extracted text."""

from dataclasses import dataclass
import re

from app.integrations.rag.corpus import CATEGORY_DESCRIPTIONS
from app.schemas.core import ExtractionResult


# Canonical labels are the only content derived from receipt descriptions/vendor.
# This deliberately sacrifices open-ended keywords to keep PII out of retrieval.
_CONCEPTS = {
    "alkohol": ("alkohol", "alcohol", "beer", "bir", "wine", "whiskey", "vodka"),
    "nota SPBU": ("spbu", "bbm", "bensin", "pertalite", "pertamax", "solar"),
    "perjalanan dinas": ("perjalanan dinas", "business trip"),
    "makan dinas": ("makan", "meal", "nasi", "lunch", "dinner"),
    "hotel menginap": ("hotel", "kamar", "menginap", "room"),
    "tol parkir": ("tol", "toll", "parkir", "parking"),
    "nota pembayaran": ("nota", "receipt", "invoice"),
}


@dataclass(frozen=True)
class PolicyQueryContext:
    concepts: tuple[str, ...] = ()
    participants: int = 1

    @classmethod
    def from_extraction(cls, extraction: ExtractionResult, participants: int = 1) -> "PolicyQueryContext":
        # Bound work as well as output. Do not read warnings, answers or raw OCR.
        parts = [str(extraction.vendor.value or "")[:500]]
        parts.extend(item.description[:255] for item in extraction.line_items[:50])
        text = " ".join(parts).casefold()
        concepts = tuple(label for label, terms in _CONCEPTS.items()
                         if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) for term in terms))
        return cls(concepts, max(1, min(participants, 1000)))


def build_query(category: str, context: PolicyQueryContext | None = None) -> str:
    if context is None or not context.concepts:
        return f"{category}: {CATEGORY_DESCRIPTIONS[category]}"
    # Revalidate even manually constructed internal contexts; no free-text seam.
    concepts = [label for label in _CONCEPTS if label in context.concepts]
    if not concepts:
        return f"{category}: {CATEGORY_DESCRIPTIONS[category]}"
    participants = max(1, min(context.participants, 1000))
    return (f"Kebijakan penggantian biaya kategori {category}; konteks: "
            f"{'; '.join(concepts)}; jumlah peserta {participants}. "
            "Cari aturan dan syarat yang berlaku untuk pengeluaran ini.")
