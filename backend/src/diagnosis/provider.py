from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


def report_model(settings):
    options = dict(api_key=settings.llm_api_key, model=settings.llm_model, temperature=0,
                   timeout=35, max_retries=1, max_tokens=min(700, settings.llm_max_output_tokens))
    if settings.llm_provider == "groq":
        return ChatGroq(**options, model_kwargs={"response_format": {"type": "json_object"}})
    if settings.llm_provider == "openai":
        return ChatOpenAI(**options, base_url=settings.llm_base_url, model_kwargs={"response_format": {"type": "json_object"}})
    raise ValueError("No report model configured")


def management_editor_model(settings, max_tokens=450):
    """Use the selected provider for one small, evidence-constrained edit."""
    options = dict(api_key=settings.llm_api_key, model=settings.llm_model, temperature=0,
                   timeout=25, max_retries=0, max_tokens=min(max_tokens, settings.llm_max_output_tokens))
    if settings.llm_provider == "groq":
        is_qwen = settings.llm_model.startswith("qwen/")
        return ChatGroq(**options, reasoning_effort="none" if is_qwen else "low", reasoning_format="hidden",
                        model_kwargs={"response_format": {"type": "json_object"}}), f"groq:{settings.llm_model}"
    if settings.llm_provider == "openai":
        kwargs = {} if "deepseek" in (settings.llm_base_url or "") else {"response_format": {"type": "json_object"}}
        return ChatOpenAI(**options, base_url=settings.llm_base_url, model_kwargs=kwargs), f"openai:{settings.llm_model}"
    raise ValueError("No management editor model configured")
