import asyncio
import re
from difflib import SequenceMatcher
from urllib.parse import urlencode

from agent_runtime.claims import unsupported_claims
from local_seo.maps import MapsLookupError, lookup_candidates
from local_seo.models import LocalResult, Page


def ground_profile(profile, prompt):
    """Extracted operational facts must have exact source support, not model invention."""
    if profile.exceeds_page_limit:
        raise ValueError("Split your request into batches of at most three locations.")
    strings = [profile.business_name, profile.phone, profile.hours, *profile.services, *profile.differentiators]
    for location in profile.locations:
        strings.extend([location.area, location.address, location.phone, location.hours, *location.local_proof])
    if any(value and value.casefold() not in prompt.casefold() for value in strings):
        raise ValueError("Some extracted business facts were not found in your brief. Please provide explicit business and branch details.")
    if len({location.area.casefold() for location in profile.locations}) != len(profile.locations):
        raise ValueError("Use one page per distinct area in this batch.")
    return profile


def finalize(profile, drafts, existing_urls, source_text=""):
    pages = []
    warnings = list(profile.missing_information)
    # Extraction is grounded verbatim against the brief, but generated prose is not.
    # Value and reputation claims the brief never made are surfaced as review tasks
    # rather than silently published inside a draft that reads as finished copy.
    supported_text = " ".join([source_text, *profile.services, *profile.differentiators])
    for index, (location, draft) in enumerate(zip(profile.locations, drafts, strict=True)):
        phone = location.phone or profile.phone
        hours = location.hours or profile.hours
        tasks = ["Review every generated claim against the supplied brief; confirm real coverage and local facts.",
                 "Validate JSON-LD before publishing; connect and test the quote or booking form separately."]
        if not location.local_proof:
            tasks.append("Add genuine local proof: a recent job, permissioned customer review or original area photo.")
        if not profile.business_name:
            tasks.append("Confirm the business name.")
        if not phone:
            tasks.append("Add a confirmed contact phone or booking destination.")
        if not hours:
            tasks.append("Confirm operating hours.")
        if location.kind in {"planned", "unknown"}:
            tasks.append("Confirm opening status and location type before publishing or offering bookings.")
        values = [draft.title, draft.meta_description, draft.headline, draft.introduction, draft.call_to_action,
                  *(s.body for s in draft.sections), *(s.heading for s in draft.sections),
                  *(f.answer for f in draft.faqs), *(f.question for f in draft.faqs)]
        if any("[" in value for value in values):
            tasks.append("Replace all draft placeholders with confirmed details.")
        claims = unsupported_claims(" ".join(values), supported_text)
        if claims:
            claim_warning = (
                f"Unsupported claim wording in the {location.area} draft: "
                + ", ".join(claims)
                + ". Remove it or supply evidence; your brief did not state this."
            )
            tasks.append(claim_warning)
            warnings.append(claim_warning)
        for proof in location.local_proof:
            if re.search(rf"(?:located|based|stay|book\w*)[^.]{{0,40}}\b(?:at|in|through)\s+{re.escape(proof)}\b", " ".join(values), re.IGNORECASE):
                misplaced = (
                    f"The {location.area} draft treats local proof '{proof}' as an address or booking "
                    "destination. Local proof is evidence, not a location; correct this before publishing."
                )
                tasks.append(misplaced)
                warnings.append(misplaced)
        if location.kind == "planned":
            tasks.append("This is a future-location draft. Remove any copy implying this office is already open.")
        if len(draft.title) > 60 or len(draft.meta_description) > 160:
            tasks.append("Review long metadata in a search-snippet preview; character counts are guidance, not display guarantees.")
        schema = {}
        if profile.business_name and location.kind not in {"planned", "unknown"}:
            provider = {"@type": "Organization", "name": profile.business_name}
            if phone:
                provider["telephone"] = phone
            if location.kind == "physical" and location.address:
                schema = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": profile.business_name, "address": location.address}
                if phone:
                    schema["telephone"] = phone
            else:
                schema = {"@context": "https://schema.org", "@type": "Service", "serviceType": list(profile.services), "areaServed": location.area, "provider": provider}
                if location.kind == "physical":
                    tasks.append(
                        "Service markup was used because no street address was supplied. Add the "
                        "branch address to switch this block to LocalBusiness, and pick the most "
                        "specific type for your sector, such as Hotel, Restaurant or Dentist."
                    )
        else:
            tasks.append("Schema withheld until business identity and operating location are confirmed.")
        slug = re.sub(r"[^a-z0-9]+", "-", (profile.services[0] + " " + location.area).lower()).strip("-")[:100]
        slug = f"/{slug or 'local-page'}-{index + 1}"
        digits = re.sub(r"[^+0-9]", "", phone)
        pages.append(Page(
            area=location.area, kind=location.kind, suggested_slug=slug, content=draft,
            business_details={"name": profile.business_name, "address": location.address if location.kind == "physical" else "", "phone": phone, "hours": hours, "area": location.area},
            json_ld=schema, title_characters=len(draft.title), description_characters=len(draft.meta_description),
            call_url=f"tel:{digits}" if digits and location.kind not in {"planned", "unknown"} else None,
            directions_url="https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": location.address}) if location.kind == "physical" and location.address else None,
            existing_link_candidates=[str(url) for url in existing_urls], review_tasks=tasks,
        ))
    for page in pages:
        page.proposed_sibling_slugs = [other.suggested_slug for other in pages if other is not page]
    for i, first in enumerate(pages):
        for second in pages[i + 1:]:
            def normalize(text):
                for location in profile.locations:
                    text = re.sub(re.escape(location.area), " AREA ", text, flags=re.I)
                return " ".join(re.findall(r"\w+", text.casefold()))
            passages_a = [first.content.introduction, *(s.body for s in first.content.sections), *(f.answer for f in first.content.faqs)]
            passages_b = [second.content.introduction, *(s.body for s in second.content.sections), *(f.answer for f in second.content.faqs)]
            if any(len(a) > 60 and SequenceMatcher(None, normalize(a), normalize(b)).ratio() >= .82 for a in passages_a for b in passages_b):
                warning = f"Similar copy across {first.area} and {second.area}; add distinct local evidence. City-name swaps are ignored in this comparison."
                warnings.append(warning)
                first.review_tasks.append(warning)
                second.review_tasks.append(warning)
    return LocalResult(profile=profile, pages=pages, warnings=warnings)


async def generate_run(request, generator, progress):
    async with asyncio.timeout(220):
        progress("extracting", 10)
        profile = ground_profile(await generator.parse(request), request.prompt)
        drafts = []
        for index, location in enumerate(profile.locations):
            progress(f"drafting_page_{index + 1}", 20 + index * 20)
            drafts.append(await generator.draft(profile, location))
        progress("validating", 85)
        result = finalize(profile, drafts, request.existing_urls, request.prompt)
    # Optional enrichment has its own budget; it cannot consume the draft deadline.
    if request.lookup_maps:
        progress("maps_references", 90)
        for location in profile.locations:
            if location.kind != "physical" or not profile.business_name:
                result.warnings.append(f"Listing lookup skipped for {location.area}: requires a named existing physical branch.")
                continue
            try:
                async with asyncio.timeout(25):
                    candidates = await lookup_candidates(profile.business_name, location.area)
                result.maps_candidates.extend(candidates)
                if not candidates:
                    result.warnings.append(f"No public OpenStreetMap listing matched {location.area}.")
            except MapsLookupError as exc:
                result.warnings.append(str(exc))
            except Exception:
                result.warnings.append("Listing lookup unavailable; draft retained. The public OpenStreetMap service may be busy — retry later.")
    return result
