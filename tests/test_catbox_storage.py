"""Testes unitários do serviço de armazenamento em nuvem Catbox (https://catbox.moe)."""
from unittest.mock import MagicMock, patch
import pytest

from app.config import CATBOX_USERHASH
from app.services.storage_service import CatboxStorageService, get_storage_service


def test_catbox_service_initialization():
    service = CatboxStorageService(userhash="test_userhash_123")
    assert service.userhash == "test_userhash_123"
    assert service.api_url == "https://catbox.moe/user/api.php"


def test_catbox_default_userhash():
    service = CatboxStorageService()
    assert service.userhash == CATBOX_USERHASH
    assert isinstance(service.userhash, str)


@patch("requests.post")
def test_catbox_save_image_success(mock_post):
    # Simula resposta bem-sucedida do servidor Catbox (retorna a URL permanente direta)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "https://files.catbox.moe/k9x8z1.jpg"
    mock_post.return_value = mock_response

    service = CatboxStorageService(userhash="YOUR_CATBOX_USERHASH")
    image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # Cabeçalho JPEG
    url = service.save_image(image_bytes, filename="bounty_test.jpg")

    assert url == "https://files.catbox.moe/k9x8z1.jpg"
    assert mock_post.called

    # Verifica os parâmetros enviados para a API do Catbox
    called_args, called_kwargs = mock_post.call_args
    assert called_args[0] == "https://catbox.moe/user/api.php"
    assert called_kwargs["data"]["reqtype"] == "fileupload"
    assert called_kwargs["data"]["userhash"] == "YOUR_CATBOX_USERHASH"
    assert "fileToUpload" in called_kwargs["files"]


@patch("requests.post")
def test_catbox_fallback_on_network_error(mock_post):
    # Simula falha de conexão na API do Catbox (timeout / offline)
    mock_post.side_effect = Exception("Connection timed out")

    service = CatboxStorageService(userhash="YOUR_CATBOX_USERHASH")
    image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    url = service.save_image(image_bytes, filename="bounty_fallback.jpg")

    # Garante que houve fallback seguro para armazenamento local sem lançar exceção
    assert url is not None
    assert "/uploads/" in url or "file://" in url or "http://" in url


def test_factory_returns_catbox_service():
    with patch.dict("os.environ", {"ECOBOUNTY_STORAGE_BACKEND": "catbox"}):
        with patch("app.config.STORAGE_BACKEND", "catbox"):
            svc = get_storage_service()
            assert isinstance(svc, CatboxStorageService)
