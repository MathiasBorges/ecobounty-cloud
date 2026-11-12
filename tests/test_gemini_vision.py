"""Testes unitários do serviço de visão computacional Google Gemini API (Multimodal Vision Free Tier)."""
import json
from unittest.mock import MagicMock, patch
import pytest

from app.services.vision_service import GeminiVisionService, get_vision_service


def test_gemini_service_initialization():
    service = GeminiVisionService(api_key="fake_key_123", model_name="gemini-1.5-flash")
    assert service.api_key == "fake_key_123"
    assert service.model_name == "gemini-1.5-flash"


def test_gemini_audit_cleaning_simulate_failure():
    service = GeminiVisionService(api_key="test_key")
    res = service.audit_cleaning(b"dummy_image", bounty_id=1, simulate_failure=True)
    assert res["approved"] is False
    assert res["confidence"] <= 0.50
    assert "Limpeza não validada" in res["message"]


def test_gemini_audit_cleaning_string_fail():
    service = GeminiVisionService(api_key="test_key")
    res = service.audit_cleaning("foto_area_suja.jpg", bounty_id=1)
    assert res["approved"] is False
    assert "Limpeza não validada" in res["message"]


def test_gemini_classify_irregular_waste_simulate_empty():
    service = GeminiVisionService(api_key="test_key")
    res = service.classify_irregular_waste(b"dummy_image", lat=-9.66, lng=-35.70, simulate_empty=True)
    assert res["identified"] is False
    assert res["waste_type"] is None
    assert res["estimated_value"] == 0.0


def test_gemini_fallback_when_no_api_key():
    service = GeminiVisionService(api_key="")
    # Deve usar o LocalVisionService de fallback de forma transparente
    audit = service.audit_cleaning(b"image_bytes", bounty_id=1)
    assert audit["approved"] is True

    classify = service.classify_irregular_waste(b"image_bytes", lat=-9.66, lng=-35.70)
    assert classify["identified"] is True
    assert classify["waste_type"] == "Plástico"


@patch("requests.post")
def test_gemini_audit_cleaning_api_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "approved": True,
                                "confidence": 0.98,
                                "message": "Área totalmente limpa pela IA Gemini!",
                                "waste_detected": None,
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    service = GeminiVisionService(api_key="real_or_mock_key")
    res = service.audit_cleaning(b"\xff\xd8\xff\xe0\x00\x10JFIF", bounty_id=10)

    assert res["approved"] is True
    assert res["confidence"] == 0.98
    assert "Área totalmente limpa" in res["message"]
    assert "Google Gemini Vision" in res["provider"]
    assert mock_post.called


@patch("requests.post")
def test_gemini_classify_waste_api_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "identified": True,
                                "waste_type": "Vidro e Garrafas",
                                "title": "Garrafas de Vidro Descartadas na Calçada",
                                "estimated_value": 35.00,
                                "dest": "COOPLUM",
                                "message": "Resíduo perfurocortante identificado com urgência.",
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    service = GeminiVisionService(api_key="real_or_mock_key")
    res = service.classify_irregular_waste(b"\xff\xd8\xff\xe0\x00\x10JFIF", lat=-9.64, lng=-35.70)

    assert res["identified"] is True
    assert res["waste_type"] == "Vidro e Garrafas"
    assert res["estimated_value"] == 35.00
    assert res["dest"] == "COOPLUM"
    assert "Google Gemini Vision" in res["provider"]


@patch("requests.post")
def test_gemini_failover_cascade_on_429_quota_exhausted(mock_post):
    """Testa transição automática de modelo quando o primeiro atinge o limite de cota (HTTP 429)."""
    # 1ª chamada (gemini-3.1-flash-lite) retorna 429 (Cota esgotada)
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.text = "RESOURCE_EXHAUSTED: Quota exceeded"

    # 2ª chamada (gemini-3.5-flash-lite) retorna 200 (Sucesso)
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "approved": True,
                                "confidence": 0.99,
                                "message": "Área limpa validada pelo modelo alternativo com sucesso.",
                                "waste_detected": None,
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_post.side_effect = [resp_429, resp_200]

    service = GeminiVisionService(
        api_key="mock_key",
        models_pool=["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"],
    )
    res = service.audit_cleaning(b"\xff\xd8\xff\xe0\x00\x10JFIF", bounty_id=99)

    assert res["approved"] is True
    assert "gemini-3.5-flash-lite" in res["provider"]
    assert mock_post.call_count == 2

