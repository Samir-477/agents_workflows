"""Inspect JSON-LD parseability on one public HTML page for evaluation review."""

from __future__ import annotations

import argparse
import json

import httpx
from bs4 import BeautifulSoup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+")
    args = parser.parse_args()
    for url in args.urls:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": "StellarAuditReview/1.0", "Accept-Encoding": "identity"},
        )
        response.raise_for_status()
        scripts = BeautifulSoup(response.text, "html.parser").find_all(
            "script", attrs={"type": "application/ld+json"}
        )
        print(f"url={response.url} status={response.status_code} blocks={len(scripts)}")
        for index, script in enumerate(scripts, 1):
            raw = script.string or script.get_text()
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    schema_type = payload.get("@type") or "dict"
                else:
                    schema_type = type(payload).__name__
                print(f"block={index} valid=true type={schema_type}")
            except (json.JSONDecodeError, TypeError) as exc:
                excerpt = " ".join(raw.split())[:240]
                print(f"block={index} valid=false error={exc} excerpt={excerpt}")


if __name__ == "__main__":
    main()
