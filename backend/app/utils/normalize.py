from typing import Any


def normalize_to_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                normalized.append(cleaned)
            continue
        cleaned = str(item).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized
