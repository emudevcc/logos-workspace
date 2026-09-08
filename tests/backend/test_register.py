"""Tests for the register-swap service and endpoint."""

import pytest

from app.services.llm import LLMNotConfiguredError
from app.services.register import RegisterService
from tests.backend.helpers import ClientFactory, FakeLLM


async def test_rewrite_returns_result() -> None:
    llm = FakeLLM(result={"rewritten": "Rewritten text"})
    result = await RegisterService(llm).rewrite("original", "Executive")
    assert result.rewritten == "Rewritten text"


async def test_rewrite_not_configured_raises() -> None:
    with pytest.raises(LLMNotConfiguredError):
        await RegisterService(FakeLLM(enabled=False)).rewrite("text", "Executive")


def test_register_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(result={"rewritten": "Rewritten text"})
    with client_factory(llm=llm) as client:
        response = client.post(
            "/api/register/rewrite", json={"text": "hey", "register_tag": "Executive"}
        )
        assert response.status_code == 200
        assert response.json()["rewritten"] == "Rewritten text"


def test_register_endpoint_polite_and_hedged(client_factory: ClientFactory) -> None:
    llm = FakeLLM(result={"rewritten": "Rewritten text"})
    with client_factory(llm=llm) as client:
        for tag in ("Polite", "Hedged"):
            response = client.post(
                "/api/register/rewrite", json={"text": "hey", "register_tag": tag}
            )
            assert response.status_code == 200
            assert response.json()["rewritten"] == "Rewritten text"
