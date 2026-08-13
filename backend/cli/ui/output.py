import json
from typing import List, Dict, Any, Optional

def print_table(headers: List[str], rows: List[List[Any]]) -> None:
    """Prints a clean ASCII table dynamically aligned to max column widths.
    If no rows are present, prints a 'No records found.' message.
    """
    if not rows:
        print("No records found.")
        return

    # Normalize all cell values to string representations
    string_rows = []
    for row in rows:
        string_rows.append([str(cell) if cell is not None else "" for cell in row])

    # Calculate required width for each column
    col_widths = [len(h) for h in headers]
    for row in string_rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    # Construct the formatting template string
    row_format = " | ".join(f"{{:<{w}}}" for w in col_widths)

    # Print headers and line divider
    print(row_format.format(*headers))
    print("-+-".join("-" * w for w in col_widths))

    # Print aligned rows
    for row in string_rows:
        padded_row = row + [""] * (len(headers) - len(row))
        print(row_format.format(*padded_row[:len(headers)]))

def print_object(data: Dict[str, Any]) -> None:
    """Prints key-value pairs formatted cleanly as a structured details block."""
    if not data:
        print("No data available.")
        return

    # Find longest key for layout padding
    max_key_len = max(len(str(k)) for k in data.keys())
    padding = max(max_key_len, 20)

    for k, v in data.items():
        if isinstance(v, (dict, list)):
            v_str = json.dumps(v, indent=2)
        else:
            v_str = str(v) if v is not None else ""
        print(f"{str(k).replace('_', ' ').capitalize():<{padding}} : {v_str}")

def print_success(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Prints a standardized success message banner optionally followed by object details."""
    print(f"\n[SUCCESS] {message}")
    if data:
        print("-" * 40)
        print_object(data)
        print("-" * 40)
