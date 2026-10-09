"""Versioned BRD section 9 corpus backed by the validated local policy records."""

from dataclasses import dataclass
from hashlib import sha256
import json

from app.integrations.policy_local import LocalPolicyRetriever
from app.schemas.core import Policy


SOURCE = "docs/BRD_Expense_Reimbursement_Agent.md#9"
CATEGORY_DESCRIPTIONS = {
    "meals": "Makan dinas: maksimal Rp75.000 per orang per hari; wajib nota; alkohol dilarang.",
    "fuel": "BBM: maksimal Rp150.000 per hari kerja; wajib nota SPBU.",
    "toll_parking": "Tol dan parkir: sesuai nominal nota; wajib nota.",
    "hotel": "Hotel: maksimal Rp600.000 per malam; wajib bukti perjalanan dinas dan nota.",
    "other": "Pengeluaran lain: tidak ada aturan kategori; keputusan konservatif tetap berlaku.",
}


@dataclass(frozen=True)
class PolicyDocument:
    policy: Policy
    text: str
    source: str = SOURCE

    @property
    def id(self) -> str:
        return f"{self.policy.policy_id}:{self.policy.version}:{self.policy.category}"


def policy_documents() -> list[PolicyDocument]:
    local = LocalPolicyRetriever()
    return [
        PolicyDocument(
            policy=policy,
            text=f"{description}\nSource: {SOURCE}\n{policy.model_dump_json()}",
        )
        for category, description in CATEGORY_DESCRIPTIONS.items()
        for policy in [local.retrieve(category=category, effective_date=local.effective_from)]
    ]


def index_fingerprint(documents: list[PolicyDocument], model_identity: str) -> str:
    from app.integrations.rag.chunking import CHUNKING_VERSION, chunk_documents

    content = json.dumps(
        {"schema": 2, "model": model_identity, "chunking": CHUNKING_VERSION,
         "chunks": [{"id": chunk.id, "text": chunk.text} for chunk in chunk_documents(documents)],
         "documents": [{"id": d.id, "source": d.source, "text": d.text,
                        "policy": d.policy.model_dump(mode="json")} for d in documents]},
        sort_keys=True, ensure_ascii=False,
    )
    return sha256(content.encode()).hexdigest()
