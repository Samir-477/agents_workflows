from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from serp_competitor.models import AnswerBoxEvidence, QuestionEvidence, SerpItem, SerpRequest


class SerperError(RuntimeError):
    pass


class SerperClient:
    def __init__(self, api_key: str | None, *, transport=None):
        self.api_key = api_key
        self.transport = transport

    async def search(self, request: SerpRequest):
        if not self.api_key:
            raise SerperError("Serper is not configured. Add SERPER_API_KEY on the server.")
        payload = {
            "q": request.target_keyword,
            "gl": request.country.lower(),
            "hl": request.language.lower(),
            "num": request.result_limit,
        }
        response = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(transport=self.transport, timeout=20) as client:
                    response = await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                        json=payload,
                    )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise SerperError("Serper could not be reached after bounded retries.") from exc
                await asyncio.sleep(0.25 * (attempt + 1))
                continue
            if response.status_code == 429 and attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            break
        if response is None or response.status_code != 200:
            status = response.status_code if response is not None else "unavailable"
            raise SerperError(f"Serper search failed with HTTP {status}; check quota and server configuration.")
        try:
            data = response.json()
        except ValueError as exc:
            raise SerperError("Serper returned malformed JSON.") from exc
        organic = []
        for item in data.get("organic", [])[: request.result_limit]:
            url = str(item.get("link") or "").strip()
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            organic.append(SerpItem(
                position=int(item.get("position") or len(organic) + 1),
                title=str(item.get("title") or parsed.netloc)[:500],
                url=url,
                snippet=str(item.get("snippet") or "")[:1500],
                domain=parsed.netloc.lower(),
            ))
        if not organic:
            raise SerperError("Serper returned no usable organic results for this query.")
        questions = [
            QuestionEvidence(
                question=str(item.get("question") or "")[:500],
                source_url=str(item.get("link")) if item.get("link") else None,
            )
            for item in data.get("peopleAlsoAsk", [])[:10]
            if item.get("question")
        ]
        related = [
            str(item.get("query"))[:300]
            for item in data.get("relatedSearches", [])[:10]
            if item.get("query")
        ]
        raw_answer = data.get("answerBox") if isinstance(data.get("answerBox"), dict) else None
        answer_box = None
        if raw_answer:
            answer = str(raw_answer.get("answer") or raw_answer.get("snippet") or "").strip()[:2000]
            if answer:
                source_url = str(raw_answer.get("link") or "").strip() or None
                if source_url:
                    parsed = urlsplit(source_url)
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        source_url = None
                answer_box = AnswerBoxEvidence(
                    title=str(raw_answer.get("title") or "").strip()[:500] or None,
                    answer=answer,
                    source_url=source_url,
                )
        return organic, questions, related, answer_box, datetime.now(UTC)
