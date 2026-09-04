from __future__ import annotations

import csv
import re
from io import StringIO

from keyword_cluster.models import KeywordItem


VOLUME_RE = re.compile(r"^[\s\"']*([0-9][0-9,]*)[\s\"']*$")


def parse_keywords(raw: str) -> tuple[list[KeywordItem], int, list[str]]:
    """Parse one keyword per line with an optional tab/comma/semicolon volume."""
    rows = [line.strip() for line in raw.splitlines() if line.strip()]
    unique: dict[str, KeywordItem] = {}
    warnings: list[str] = []
    for line in rows:
        parts = next(csv.reader(StringIO(line), skipinitialspace=True))
        if "\t" in line:
            parts = [part.strip() for part in line.split("\t")]
        elif ";" in line:
            parts = [part.strip() for part in line.rsplit(";", 1)]
        elif len(parts) > 2 and all(part.strip().isdigit() for part in parts[1:]):
            # A friendly paste format such as ``keyword, 1,200`` should treat
            # the final comma-separated pieces as one volume, not as keywords.
            parts = [parts[0], "".join(parts[1:])]
        keyword = parts[0].strip().strip('"\'')
        volume = None
        if len(parts) > 1:
            match = VOLUME_RE.match(parts[-1])
            if match:
                volume = int(match.group(1).replace(",", ""))
            else:
                keyword = line.strip().strip('"\'')
        keyword = re.sub(r"\s+", " ", keyword)
        if not keyword:
            continue
        key = keyword.casefold()
        current = unique.get(key)
        if current is None or (volume is not None and (current.volume is None or volume > current.volume)):
            unique[key] = KeywordItem(keyword=keyword, volume=volume)
    duplicates = max(0, len(rows) - len(unique))
    if duplicates:
        warnings.append(f"Removed {duplicates} duplicate keyword row{'s' if duplicates != 1 else ''}.")
    if not any(item.volume is not None for item in unique.values()):
        warnings.append("No search volumes were supplied, so priority relies on intent and architecture fit.")
    return list(unique.values()), duplicates, warnings
