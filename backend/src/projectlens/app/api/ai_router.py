"""Opt-in AI explanations over persisted structured snapshots."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from projectlens.ai.clients import AnthropicProvider, OpenAIProvider, OpenAICompatibleProvider
from projectlens.ai.explain import ExplainError, complete_request, explain
from projectlens.ai.provider import AIProvider, AIRequest, AIUnavailableError
from projectlens.ai.settings import AIConfigurationError, get_ai_settings, resolve_provider_settings
from projectlens.app.api.dependencies import get_session
from projectlens.app.db.repository import get_latest_snapshot, get_project, get_snapshot_for_project

router = APIRouter()


class ExplanationRequest(BaseModel):
    kind: str
    snapshot: str = "latest"


def get_ai_provider(request: Request) -> AIProvider:
    """Construct a provider per request; credentials are never persisted or cached."""
    try:
        # Reject ambiguous duplicate headers, without reflecting any input.
        for name in ("x-ai-provider", "x-ai-model", "x-ai-base-url", "x-ai-key"):
            if len(request.headers.getlist(name)) > 1:
                raise AIConfigurationError("Duplicate AI headers are not supported.")
        config = resolve_provider_settings(request.headers)
    except AIConfigurationError:
        raise HTTPException(422, detail={"code": "validation_error", "message": "Invalid AI provider headers or environment configuration."}) from None
    if config is not None:
        if config.provider == "anthropic":
            return AnthropicProvider(config.api_key, config.model)
        if config.provider == "openai":
            return OpenAIProvider(config.api_key, config.model)
        return OpenAICompatibleProvider(config.base_url, config.model, config.api_key)

    class UnconfiguredProvider:
        name = "unconfigured"
        model = "unconfigured"

        def complete(self, request):
            raise AIUnavailableError("No AI provider is configured.")
    return UnconfiguredProvider()


def _user_supplied_provider(request: Request) -> bool:
    """A user who sends their own provider credentials has opted in for that request."""
    return bool(request.headers.get("x-ai-provider") or request.headers.get("x-ai-key"))


def _provider_error(exc: ExplainError) -> HTTPException:
    status = (401 if exc.code == "ai_auth_failed" else
              503 if exc.code in {"ai_timeout", "ai_unavailable", "ai_provider_error"} else 502)
    return HTTPException(status, detail={"code": exc.code, "message": exc.message})


@router.post("/ai/test")
def test_ai_connection(request: Request, provider: AIProvider = Depends(get_ai_provider)):
    settings = get_ai_settings()
    if not (settings.enabled or _user_supplied_provider(request)):
        raise HTTPException(503, detail={"code": "ai_disabled", "message": "AI explanations are disabled."})
    try:
        response = complete_request(provider, AIRequest(
            "You are testing a connection. Reply briefly.", "Reply with OK.", 16, settings.timeout_s))
    except ExplainError as exc:
        raise _provider_error(exc) from None
    return {"ok": True, "provider": getattr(provider, "name", "fake"), "model": response.model}


@router.post("/projects/{project_id}/ai/explanations")
def create_explanation(project_id: int, body: ExplanationRequest, request: Request,
                       session: Session = Depends(get_session),
                       provider: AIProvider = Depends(get_ai_provider)):
    settings = get_ai_settings()
    if not (settings.enabled or _user_supplied_provider(request)):
        raise HTTPException(503, detail={"code": "ai_disabled", "message": "AI explanations are disabled."})
    if body.kind not in {"repository", "architecture", "risk"}:
        raise HTTPException(422, detail={"code": "validation_error", "message": "kind must be repository, architecture, or risk."})
    if get_project(session, project_id=project_id) is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project was not found."})
    if body.snapshot == "latest":
        selected = get_latest_snapshot(session, project_id)
        if selected is None:
            raise HTTPException(409, detail={"code": "snapshot_not_found", "message": "No snapshot is available for this project."})
    elif re.fullmatch(r"[0-9]+", body.snapshot):
        selected = get_snapshot_for_project(session, project_id, int(body.snapshot))
        if selected is None:
            raise HTTPException(404, detail={"code": "snapshot_not_found", "message": "Snapshot was not found for this project."})
    else:
        raise HTTPException(422, detail={"code": "validation_error", "message": "snapshot must be 'latest' or a snapshot ID."})
    try:
        return explain(selected.result_json, body.kind, provider, max_bytes=settings.max_context_bytes,
                       max_output_tokens=settings.max_output_tokens, timeout_s=settings.timeout_s)
    except ExplainError as exc:
        raise _provider_error(exc) from None
