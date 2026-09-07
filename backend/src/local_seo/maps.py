"""Keyless listing lookup over public OpenStreetMap services.

No API key, no billing, open data only. The area string is resolved to a bounding
box with Nominatim, then Overpass returns named points of interest inside it. We
keep only the OSM id, the matched name and a link; listing tags are never stored,
and every upstream string is treated as untrusted text, not instructions.
"""

import difflib
import re

import httpx

_USER_AGENT = "stellar-local-seo/0.1 (+local-page draft listing check; open-data OSM)"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_POI_KEYS = (
    "shop", "amenity", "office", "craft", "healthcare",
    "tourism", "leisure", "club", "company", "trade",
)
_WORD = re.compile(r"[A-Za-z0-9]+")
_OSM_TYPES = {"node", "way", "relation"}
_MAX_SPAN_DEGREES = 2.0


class MapsLookupError(ValueError):
    """Safe diagnostics only; never retain an upstream error body or response text."""

    def __init__(self, status_code, reasons):
        self.status_code = status_code
        self.reasons = [
            reason
            for reason in reasons
            if isinstance(reason, str) and re.fullmatch(r"[A-Z_]{3,80}", reason)
        ]
        super().__init__(
            f"Listing lookup unavailable (HTTP {status_code}; {', '.join(self.reasons) or 'UNKNOWN'}). "
            "The public OpenStreetMap services may be busy or rate-limiting; the draft is unaffected. Retry later."
        )


def _search_token(business: str) -> str:
    """Longest alphanumeric word from the name, so the Overpass regex stays safe."""
    words = _WORD.findall(business or "")
    return max(words, key=len) if words else ""


def _clean_name(value: object) -> str:
    return re.sub(r"\s+", " ", value).strip()[:120] if isinstance(value, str) else ""


async def _bounding_box(session, area: str):
    """Resolve a free-text area to (south, west, north, east) or None."""
    response = await session.get(
        _NOMINATIM_URL,
        params={"q": area, "format": "jsonv2", "limit": 1, "addressdetails": 0},
        headers={"User-Agent": _USER_AGENT, "Accept-Language": "en"},
    )
    if response.status_code != 200:
        raise MapsLookupError(response.status_code, ["NOMINATIM_UNAVAILABLE"])
    rows = response.json()
    if not isinstance(rows, list) or not rows or "boundingbox" not in rows[0]:
        return None
    try:
        south, north, west, east = (float(value) for value in rows[0]["boundingbox"])
    except (TypeError, ValueError):
        return None
    if abs(north - south) > _MAX_SPAN_DEGREES or abs(east - west) > _MAX_SPAN_DEGREES:
        return None
    return south, west, north, east


async def _named_elements(session, token: str, bbox) -> list[dict]:
    south, west, north, east = bbox
    query = (
        "[out:json][timeout:20];"
        f'nwr["name"~"{token}",i]({south:.5f},{west:.5f},{north:.5f},{east:.5f});'
        "out center 25;"
    )
    response = await session.post(
        _OVERPASS_URL, data={"data": query}, headers={"User-Agent": _USER_AGENT}
    )
    if response.status_code != 200:
        raise MapsLookupError(response.status_code, ["OVERPASS_UNAVAILABLE"])
    payload = response.json()
    elements = payload.get("elements", []) if isinstance(payload, dict) else []
    return [element for element in elements if isinstance(element, dict)]


async def lookup_candidates(business: str, area: str, *, client=None) -> list[dict[str, str]]:
    """Keyless IDs-only OpenStreetMap lookup. Never persists listing tags."""
    token = _search_token(business)
    if not token or not area:
        return []

    async def run(session):
        bbox = await _bounding_box(session, area)
        if bbox is None:
            return []
        target = business.casefold()
        scored: list[tuple[float, dict[str, str]]] = []
        for element in await _named_elements(session, token, bbox):
            tags = element.get("tags", {})
            if not isinstance(tags, dict):
                continue
            name = _clean_name(tags.get("name"))
            osm_type = element.get("type")
            osm_id = element.get("id")
            if not name or osm_type not in _OSM_TYPES or not isinstance(osm_id, int):
                continue
            if not any(key in tags for key in _POI_KEYS):
                continue
            folded = name.casefold()
            ratio = difflib.SequenceMatcher(None, target, folded).ratio()
            if target not in folded and folded not in target and ratio < 0.6:
                continue
            ref = f"{osm_type}/{osm_id}"
            scored.append((ratio, {
                "place_id": ref,
                "area": area,
                "name": name,
                "maps_url": f"https://www.openstreetmap.org/{ref}",
            }))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in scored[:3]]

    if client is not None:
        return await run(client)
    async with httpx.AsyncClient(
        timeout=20, follow_redirects=False, headers={"User-Agent": _USER_AGENT}
    ) as session:
        return await run(session)
