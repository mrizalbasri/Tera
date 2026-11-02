"""Explicit synthetic relevance/latency evaluation, outside API requests."""

from dataclasses import dataclass
from statistics import mean
from time import perf_counter
from typing import TypedDict

from app.integrations.rag.corpus import policy_documents
from app.integrations.rag.query import PolicyQueryContext, build_query
from app.integrations.rag.reranker import Reranker, rerank_candidates
from app.integrations.rag.search import PolicySearch


@dataclass(frozen=True)
class BenchmarkCase:
    category: str
    concepts: tuple[str, ...]
    expected_rule: str


CASES = (
    BenchmarkCase("meals", ("alkohol",), "prohibited_items"),
    BenchmarkCase("fuel", ("alkohol",), "prohibited_items"),
    BenchmarkCase("hotel", ("alkohol",), "prohibited_items"),
    BenchmarkCase("toll_parking", ("alkohol",), "prohibited_items"),
    BenchmarkCase("fuel", ("nota SPBU",), "fuel_spbu_required"),
    BenchmarkCase("hotel", ("perjalanan dinas",), "hotel_business_trip_required"),
    BenchmarkCase("meals", ("nota pembayaran",), "receipt_required"),
    BenchmarkCase("hotel", ("nota pembayaran",), "receipt_required"),
    BenchmarkCase("toll_parking", ("tol parkir",), "toll_amount_matches"),
)


class BenchmarkResult(TypedDict):
    cases: int
    top_k: int
    top_n: int
    search_top1: float
    reranked_top1: float
    search_mrr_at_n: float
    reranked_mrr_at_n: float
    mean_search_ms: float
    mean_rerank_ms: float


def benchmark(
    search: PolicySearch, reranker: Reranker, *, top_k: int, top_n: int,
) -> BenchmarkResult:
    """No claim data: fixed synthetic concepts; exclude first inference from latency."""
    policies = {document.policy.category: document.policy for document in policy_documents()}
    samples = []
    for _ in range(2):
        samples = []
        for case in CASES:
            query = build_query(case.category, PolicyQueryContext(case.concepts))
            started = perf_counter()
            candidates = search.search(query, category=case.category,
                                       effective_date=policies[case.category].effective_from, top_k=top_k)
            search_ms = (perf_counter() - started) * 1000
            started = perf_counter()
            ranked = rerank_candidates(query, candidates, reranker, top_n)
            rerank_ms = (perf_counter() - started) * 1000
            before = next((i for i, c in enumerate(candidates, 1) if c.rule_id == case.expected_rule), None)
            after = next((i for i, c in enumerate(ranked, 1) if c.rule_id == case.expected_rule), None)
            samples.append((before, after, search_ms, rerank_ms))
    return {
        "cases": len(samples), "top_k": top_k, "top_n": top_n,
        "search_top1": mean(before == 1 for before, _, _, _ in samples),
        "reranked_top1": mean(after == 1 for _, after, _, _ in samples),
        "search_mrr_at_n": mean(1 / before if before and before <= top_n else 0 for before, _, _, _ in samples),
        "reranked_mrr_at_n": mean(1 / after if after else 0 for _, after, _, _ in samples),
        "mean_search_ms": round(mean(ms for _, _, ms, _ in samples), 2),
        "mean_rerank_ms": round(mean(ms for _, _, _, ms in samples), 2),
    }
