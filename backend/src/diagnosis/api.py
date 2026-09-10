import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from diagnosis.models import DiagnosisInput
from diagnosis.engine import process_one, retry, rerun_all, cancel
from diagnosis.pdf import build_pdf
from diagnosis.reporting import assemble_report
from agent_runtime.session import session_subject


def public(run):
    data = run.model_dump(mode="json")
    data.pop("owner_subject", None)
    # Raw evidence stays persisted, available through the evidence endpoint.
    for key, task in data["tasks"].items():
        task.pop("token", None)
        task["result"] = {"reason": task["result"].get("reason")} if key != "report" else {}
    return data


def require_access(request: Request) -> str:
    subject = session_subject(request.cookies.get("stellar_demo_session"))
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to access website diagnoses.",
        )
    return subject


def create_router(repository, deps):
    router = APIRouter(
        prefix="/api/diagnoses",
        tags=["Website Diagnosis"],
        dependencies=[Depends(require_access)],
    )
    def get(id, subject):
        try:
            run = repository.get(id)
        except LookupError:
            raise HTTPException(404, "Diagnosis not found") from None
        legacy_admin = run.owner_subject is None and subject in {"admin", "local-demo-admin"}
        if run.owner_subject != subject and not legacy_admin:
            raise HTTPException(404, "Diagnosis not found")
        return run

    @router.post("", status_code=202)
    def create(payload: DiagnosisInput, subject: str = Depends(require_access)):
        created = repository.create(payload)
        repository.mutate(created.id, lambda run: setattr(run, "owner_subject", subject))
        return public(repository.get(created.id))

    @router.get("")
    def history(subject: str = Depends(require_access)):
        visible = [r for r in repository.list() if r.owner_subject == subject or (r.owner_subject is None and subject in {"admin", "local-demo-admin"})]
        return [{"id": r.id, "url": str(r.request.page_url), "status": r.status, "created_at": r.created_at} for r in visible]

    @router.get("/{id}")
    def read(id: str, subject: str = Depends(require_access)):
        return public(get(id, subject))

    @router.post("/{id}/advance")
    async def advance(id: str, subject: str = Depends(require_access)):
        get(id, subject)
        return public(await process_one(deps, repository, id))

    @router.post("/{id}/retry")
    def retry_run(id: str, subject: str = Depends(require_access)):
        get(id, subject)
        try:
            return public(retry(repository, id))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @router.post("/{id}/upgrade")
    def upgrade_run(id: str, subject: str = Depends(require_access)):
        current = get(id, subject)
        if current.report and current.report.get("version", 0) >= 5:
            raise HTTPException(409, "This diagnosis already uses the current evidence contract.")
        try:
            return public(rerun_all(repository, id))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @router.post("/{id}/rerun-all")
    def rerun_all_tasks(id: str, subject: str = Depends(require_access)):
        """Start a fresh evidence capture and rerun all ten specialists."""
        get(id, subject)
        try:
            return public(rerun_all(repository, id))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @router.post("/{id}/cancel")
    def cancel_run(id: str, subject: str = Depends(require_access)):
        get(id, subject)
        return public(cancel(repository, id))

    @router.post("/{id}/refresh-report")
    async def refresh_report(id: str, subject: str = Depends(require_access)):
        """Rebuild presentation data from the already saved agent evidence."""
        current = get(id, subject)
        if current.tasks["capture"].status != "complete":
            raise HTTPException(409, "Captured evidence is not available yet.")
        report = assemble_report(current)
        try:
            from diagnosis.reporting import narrate
            settings = deps.settings
            generator = deps.metadata_generator
            from dataclasses import replace
            if current.request.model_provider == "deepseek":
                settings = replace(settings, llm_provider="openai", llm_api_key=os.getenv("DEEPSEEK_API_KEY"),
                                   llm_model=os.getenv("DEEPSEEK_MODEL"), llm_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
            else:
                settings = replace(
                    settings,
                    llm_api_key=generator.api_key_resolver(settings.llm_provider, settings.llm_api_key) if generator.api_key_resolver else settings.llm_api_key,
                    llm_model=generator.model_resolver(settings.llm_model) if generator.model_resolver else settings.llm_model,
                )
            report = await narrate(report, settings)
        except Exception:
            report["management_editor"]["note"] = "The editorial model was unavailable; deterministic management wording is shown."
        def rebuild(run):
            run.report = report
            run.tasks["report"].result = {"report_version": run.report["version"]}
            return run
        repository.mutate(id, rebuild)
        return public(get(id, subject))

    @router.get("/{id}/evidence")
    def evidence(id: str, subject: str = Depends(require_access)):
        return {"capture": get(id, subject).tasks["capture"].result}

    @router.get("/{id}/report.pdf")
    def pdf(id: str, subject: str = Depends(require_access)):
        report = get(id, subject).report
        if report is None:
            raise HTTPException(409, "Report is not ready")
        return Response(build_pdf(report), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="resort-diagnosis-{id}.pdf"', "Cache-Control": "private, no-store"})
    return router
