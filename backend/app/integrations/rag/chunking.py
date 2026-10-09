"""Atomic policy rules: retrieval can rank evidence without dropping obligations."""

from dataclasses import dataclass

from app.integrations.rag.corpus import PolicyDocument
from app.schemas.core import PolicyRule


CHUNKING_VERSION = "atomic-rules-v1"


@dataclass(frozen=True)
class PolicyChunk:
    id: str
    document_id: str
    rule_id: str
    text: str


def _rule_description(rule: PolicyRule) -> str:
    descriptions = {
        "max_amount_per_person": f"Batas nominal makan dinas per orang: {rule.currency} {rule.limit}.",
        "max_amount": f"Batas nominal pengeluaran: {rule.currency} {rule.limit}.",
        "receipt_required": "Bukti nota pembayaran wajib dilampirkan untuk klaim.",
        "vendor_required": f"Vendor wajib memenuhi syarat: {', '.join(rule.required_terms)}.",
        "evidence_required": f"Bukti pendukung wajib tersedia: {', '.join(rule.required_terms)}.",
        "amount_matches_declared": "Nominal klaim tol/parkir harus sama dengan nominal nota.",
        "prohibited_items": f"Item dilarang dan tidak boleh diganti: {', '.join(rule.prohibited_terms)}.",
    }
    return descriptions.get(rule.rule_type, "Aturan kebijakan; seluruh syarat tercantum pada record berikut.")


def chunk_documents(documents: list[PolicyDocument]) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for document in documents:
        policy = document.policy
        header = (f"Kategori {policy.category}; kebijakan {policy.policy_id} versi {policy.version}; "
                  f"berlaku {policy.effective_from} sampai {policy.effective_to or 'seterusnya'}.\n"
                  f"Source: {document.source}\n")
        for rule in policy.rules:
            chunks.append(PolicyChunk(
                id=f"{document.id}:{rule.rule_id}", document_id=document.id,
                rule_id=rule.rule_id,
                text=header + _rule_description(rule) + "\n" + rule.model_dump_json(),
            ))
        if not policy.rules:
            chunks.append(PolicyChunk(
                id=f"{document.id}:summary", document_id=document.id, rule_id="summary",
                text=header + document.text,
            ))
    if len({chunk.id for chunk in chunks}) != len(chunks):
        raise ValueError("duplicate_policy_chunk_id")
    return chunks
