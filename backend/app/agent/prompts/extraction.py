"""Receipt extraction instructions, independent of provider transport."""

EXTRACTION_PROMPT = (
    "You are an expense receipt parser. Extract the vendor, receipt date, "
    "total, currency, and category from this receipt image. Category must be "
    "one of: meals, fuel, toll_parking, hotel, other. Give every field the "
    "same confidence between 0 and 1. Return only a valid JSON object, without "
    "Markdown or extra text, using these fields and types: "
    "vendor: non-empty string (maximum 255 characters); "
    "receipt_date: string in YYYY-MM-DD format; total: positive number; "
    "currency: three-letter currency string; category: string from the list above; "
    "quantity: positive number (use 1 if unspecified); "
    "confidence: number between 0 and 1; warnings: array of strings "
    "(use an empty array if there are no warnings)."
)
