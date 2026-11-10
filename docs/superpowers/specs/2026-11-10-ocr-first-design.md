# OCR-first receipt extraction

Approved direction: local OCR first, deterministic validation for clear receipts,
and the configured live model only for ambiguous evidence. This does not change
the model provider or enable mock fallback in production.

## Scope

- Add an opt-in `RECEIPT_EXTRACTION_MODE=ocr_first` for live mode; `vision` keeps
  the existing path available for rollback.
- Use pinned RapidOCR and ONNX Runtime on CPU. Load bundled models during startup,
  reuse one engine per process, serialize inference, and bound CPU threads.
  Missing dependencies/models fail readiness instead of silently using AI.
- Group OCR boxes into reading rows. Only a narrow, fully reconciled receipt
  shape bypasses AI: readable vendor/date, explicit IDR total, complete printed
  quantity/unit-price/item-total rows, supported category, and matching arithmetic.
  Unknown rows, conflicting totals and weak readings never become invented data.
- For readable but unfamiliar layouts, send masked OCR text, not the image, to
  the existing structured extractor. Weak/empty OCR uses the existing vision path.
  The image privacy block still prevents external fallback.
- Cache OCR rows briefly in bounded process memory, keyed by content digest.
  Do not persist or log raw OCR text, images, or model responses.
- Keep downstream policy, line-item, duplicate, and amount validation unchanged.
- Reuse one progress card on retry, with retry/detail actions in that card.

## Validation and rollout

Test routing, arithmetic ambiguity, incomplete/prohibited items, privacy,
bounded caching, dependency reuse, readiness, and the real claim-processing seam.
Run real local inference on a generated synthetic receipt and report cold/warm
timings separately; synthetic success is not general receipt accuracy.

Deploy only after staging receipt evaluation on the target CPU/RAM. Enable the
mode explicitly and verify readiness. Background jobs, PDF rasterization,
cropped-image fallback, and broad receipt-template support are follow-up work;
this change does not claim to remove synchronous-request timeout risks.
