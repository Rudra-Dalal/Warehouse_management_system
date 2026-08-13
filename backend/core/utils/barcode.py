def normalize_barcode(barcode: str) -> str:
    """Accepts a barcode string, strips accidental surrounding whitespace,
    rejects empty inputs, and preserves leading zeros.
    """
    if not barcode:
        raise ValueError("Barcode cannot be empty")
    cleaned = str(barcode).strip()
    if not cleaned:
        raise ValueError("Barcode cannot be empty or only whitespace")
    return cleaned
