from app.schemas.core import Decision, Signal, TimelineEntry


DUPLICATE_MESSAGE = "Nota ini terindikasi pernah diajukan. Hubungi admin untuk peninjauan."


def employee_signal(signal: Signal) -> Signal:
    if signal.signal_type != "duplicate":
        return signal
    return signal.model_copy(update={
        "matched_claim_ids": [], "evidence": {}, "explanation": DUPLICATE_MESSAGE,
    })


def employee_decision(decision: Decision | None) -> Decision | None:
    if decision is None or "duplicate_receipt" not in decision.reason_codes:
        return decision
    return decision.model_copy(update={"explanation": DUPLICATE_MESSAGE})


def employee_timeline(entry: TimelineEntry) -> TimelineEntry:
    if entry.step_name != "signal.duplicate":
        return entry
    return entry.model_copy(update={"summary": DUPLICATE_MESSAGE})
