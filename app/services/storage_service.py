"""Serviço de Armazenamento de Arquivos e Imagens.

Interface desacoplada (Service Pattern) para persistência local (custo zero)
e chaveamento direto para Microsoft Azure Blob Storage (Projeto UNIMA Cloud).
"""
import io
import os
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from app.config import (
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_STORAGE_CONTAINER,
    CATBOX_USERHASH,
    STORAGE_BACKEND,
    UPLOADS_DIR,
)

# Caches em memória para mapeamento instantâneo de URLs e Base64 no Flet Web/CanvasKit
_URL_TO_LOCAL_PATH: Dict[str, Path] = {}
_URL_TO_B64: Dict[str, str] = {}


class StorageService(ABC):
    """Interface abstrata para armazenamento de arquivos."""

    @abstractmethod
    def save_image(self, file_bytes: bytes, extension: str = "jpg") -> str:
        """Salva a imagem e retorna o caminho ou URL acessível."""
        pass

    @abstractmethod
    def get_image_url(self, file_identifier: str) -> str:
        """Retorna o caminho ou URL para exibição da imagem."""
        pass

    @abstractmethod
    def get_physical_path(self, file_identifier: str) -> Path:
        """Retorna o caminho físico do arquivo no sistema operacional."""
        pass


class LocalStorageService(StorageService):
    """Implementação local-first (100% gratuita no sistema de arquivos)."""

    def __init__(self, upload_dir: Optional[Union[str, Path]] = None):
        self.upload_dir = Path(upload_dir) if upload_dir else UPLOADS_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_image(self, file_bytes: bytes, extension: str = "jpg") -> str:
        ext = extension.lstrip(".") or "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = self.upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        rel_url = f"/uploads/{filename}"
        _URL_TO_LOCAL_PATH[rel_url] = file_path
        _URL_TO_LOCAL_PATH[filename] = file_path
        try:
            import base64
            b64_val = base64.b64encode(file_bytes).decode("ascii")
            _URL_TO_B64[rel_url] = b64_val
            _URL_TO_B64[filename] = b64_val
        except Exception:
            pass
        # Retorna URL relativa '/uploads/{filename}' compatível com Flet Web e Desktop
        return rel_url

    def save_image_from_file(self, source_path: Union[str, Path]) -> str:
        """Lê um arquivo do sistema de arquivos e o armazena no diretório de uploads."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Arquivo de origem não encontrado: {source_path}")
        with open(source, "rb") as f:
            data = f.read()
        return self.save_image(data, extension=source.suffix or "jpg")

    def get_physical_path(self, file_identifier: str) -> Path:
        """Obtém o caminho físico real do arquivo no disco local."""
        filename = Path(file_identifier).name
        return self.upload_dir / filename

    def get_image_url(self, file_identifier: str) -> str:
        if not file_identifier:
            return ""
        if file_identifier.startswith("http://") or file_identifier.startswith("https://") or file_identifier.startswith("data:"):
            return file_identifier
        path = Path(file_identifier)
        if "uploads" in path.parts:
            idx = path.parts.index("uploads")
            return f"/{'/'.join(path.parts[idx:])}"
        filename = path.name
        return f"/uploads/{filename}"

    def create_sample_photo(
        self,
        label: str = "Descarte Irregular",
        lat: float = -9.664,
        lng: float = -35.732,
        is_clean: bool = False,
    ) -> str:
        """Gera uma foto real em formato JPEG com metadados de câmera, GPS e carimbo."""
        try:
            from PIL import Image, ImageDraw
            width, height = 800, 600
            base_color = (46, 125, 50) if is_clean else (74, 85, 104)
            img = Image.new("RGB", (width, height), color=base_color)
            draw = ImageDraw.Draw(img)

            # Elementos gráficos da foto
            if is_clean:
                draw.rectangle([40, 40, width - 40, height - 40], outline=(129, 199, 132), width=4)
                draw.text((60, 60), "ÁREA AUDITADA • LIMPEZA CONFIRMADA", fill=(255, 255, 255))
            else:
                draw.rectangle([40, 40, width - 40, height - 40], outline=(239, 68, 68), width=4)
                draw.text((60, 60), f"DENÚNCIA ECOBOUNTY: {label.upper()}", fill=(255, 255, 255))

            now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            draw.text((60, 100), f"GPS: Lat {lat:.5f}, Lng {lng:.5f} (Maceió - AL)", fill=(203, 213, 225))
            draw.text((60, 130), f"Data/Hora: {now_str}", fill=(203, 213, 225))
            draw.text((60, height - 80), "Dispositivo: Câmera Integrada EcoBounty", fill=(148, 163, 184))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return self.save_image(buf.getvalue(), "jpg")
        except Exception:
            # Fallback básico caso PIL falhe
            dummy = f"EcoBounty Photo {datetime.now().isoformat()}".encode("utf-8")
            return self.save_image(dummy, "jpg")


class AzureBlobStorageService(StorageService):
    """Implementação para Microsoft Azure Blob Storage."""

    def __init__(self, connection_string: str = "", container_name: str = ""):
        self.connection_string = connection_string or AZURE_STORAGE_CONNECTION_STRING
        self.container_name = container_name or AZURE_STORAGE_CONTAINER
        self._client = None
        self._fallback_local = LocalStorageService()

        if self.connection_string:
            try:
                import importlib
                azure_blob = importlib.import_module("azure.storage.blob")
                self._client = azure_blob.BlobServiceClient.from_connection_string(self.connection_string)
            except Exception:
                self._client = None

    def save_image(self, file_bytes: bytes, extension: str = "jpg") -> str:
        if not self._client:
            # Fallback seguro para armazenamento local caso as credenciais Azure não estejam configuradas
            return self._fallback_local.save_image(file_bytes, extension)

        blob_name = f"bounties/{uuid.uuid4().hex}.{extension.lstrip('.')}"
        container_client = self._client.get_container_client(self.container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file_bytes, overwrite=True)
        return blob_client.url

    def get_image_url(self, file_identifier: str) -> str:
        return file_identifier

    def get_physical_path(self, file_identifier: str) -> Path:
        return self._fallback_local.get_physical_path(file_identifier)


class FirebaseStorageService(StorageService):
    """Implementação para Google Cloud Platform & Firebase Storage."""

    def __init__(self):
        from app.cloud.gcp_provider import get_gcp_provider
        self.provider = get_gcp_provider()
        self._fallback_local = LocalStorageService()

    def save_image(self, file_bytes: bytes, extension: str = "jpg") -> str:
        local_url = self._fallback_local.save_image(file_bytes, extension)
        try:
            cloud_url = self.provider.upload_image(file_bytes, filename=f"bounties/{uuid.uuid4().hex}.{extension.lstrip('.')}")
            return cloud_url or local_url
        except Exception:
            return local_url

    def save_image_from_file(self, source_path: Union[str, Path]) -> str:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source_path}")
        with open(source, "rb") as f:
            data = f.read()
        return self.save_image(data, extension=source.suffix or "jpg")

    def get_image_url(self, file_identifier: str) -> str:
        if not file_identifier:
            return ""
        if file_identifier.startswith("http://") or file_identifier.startswith("https://"):
            return file_identifier
        return self._fallback_local.get_image_url(file_identifier)

    def get_physical_path(self, file_identifier: str) -> Path:
        return self._fallback_local.get_physical_path(file_identifier)

    def create_sample_photo(
        self,
        label: str = "Descarte Irregular",
        lat: float = -9.664,
        lng: float = -35.732,
        is_clean: bool = False,
    ) -> str:
        return self._fallback_local.create_sample_photo(label=label, lat=lat, lng=lng, is_clean=is_clean)


class CatboxStorageService(StorageService):
    """Implementação para Catbox (Hospedagem rápida, gratuita e permanente - https://catbox.moe).

    Suporta uploads com `userhash` da conta registrada ou anônimo, retornando links permanentes
    da CDN oficial `https://files.catbox.moe/...`. Possui fallback local transparente.
    """

    CATBOX_API_URL = "https://catbox.moe/user/api.php"

    def __init__(self, userhash: Optional[str] = None):
        self.userhash = userhash if userhash is not None else CATBOX_USERHASH
        self.api_url = self.CATBOX_API_URL
        self._fallback_local = LocalStorageService()

    def save_image(self, file_bytes: bytes, extension: str = "jpg", filename: Optional[str] = None) -> str:
        """Envia a imagem para o Catbox e retorna a URL permanente na nuvem."""
        if filename and "." in filename:
            ext = filename.split(".")[-1].lower()
        else:
            ext = extension.lstrip(".") or "jpg"

        target_name = filename or f"ecobounty_{uuid.uuid4().hex[:12]}.{ext}"

        # Sempre preserva uma cópia no disco local para cache offline e renderização imediata
        local_url = self._fallback_local.save_image(file_bytes, extension=ext)

        try:
            import requests
            data = {"reqtype": "fileupload"}
            if self.userhash:
                data["userhash"] = self.userhash.strip()

            mime = "image/png" if ext == "png" else "image/jpeg"
            files = {"fileToUpload": (target_name, file_bytes, mime)}

            resp = requests.post(self.CATBOX_API_URL, data=data, files=files, timeout=12)
            if resp.status_code == 200:
                result_url = resp.text.strip()
                if result_url.startswith("http://") or result_url.startswith("https://"):
                    phys = self._fallback_local.get_physical_path(local_url)
                    _URL_TO_LOCAL_PATH[result_url] = phys
                    try:
                        import base64
                        _URL_TO_B64[result_url] = base64.b64encode(file_bytes).decode("ascii")
                    except Exception:
                        pass
                    return result_url
        except Exception:
            pass

        return local_url

    def save_image_from_file(self, source_path: Union[str, Path]) -> str:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source_path}")
        with open(source, "rb") as f:
            data = f.read()
        return self.save_image(data, extension=source.suffix or "jpg")

    def get_image_url(self, file_identifier: str) -> str:
        if not file_identifier:
            return ""
        if file_identifier.startswith("http://") or file_identifier.startswith("https://"):
            return file_identifier
        return self._fallback_local.get_image_url(file_identifier)

    def get_physical_path(self, file_identifier: str) -> Path:
        return self._fallback_local.get_physical_path(file_identifier)

    def create_sample_photo(
        self,
        label: str = "Descarte Irregular",
        lat: float = -9.664,
        lng: float = -35.732,
        is_clean: bool = False,
    ) -> str:
        return self._fallback_local.create_sample_photo(label=label, lat=lat, lng=lng, is_clean=is_clean)


def get_image_base64(file_identifier: Optional[str]) -> Optional[str]:
    """Recupera imagem codificada em base64 para renderização direta em Flutter Web sem requisições HTTP."""
    if not file_identifier:
        return None
    if file_identifier.startswith("data:image"):
        if "," in file_identifier:
            return file_identifier.split(",", 1)[1]
        return file_identifier

    # Verifica cache em memória
    if file_identifier in _URL_TO_B64:
        return _URL_TO_B64[file_identifier]

    # Se for URL remota (Catbox, Unsplash, etc.):
    if file_identifier.startswith("http://") or file_identifier.startswith("https://"):
        if file_identifier in _URL_TO_LOCAL_PATH:
            p = _URL_TO_LOCAL_PATH[file_identifier]
            if p.exists() and p.is_file():
                try:
                    import base64
                    with open(p, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("ascii")
                        _URL_TO_B64[file_identifier] = b64
                        return b64
                except Exception:
                    pass
        # Tenta download rápido para cache em memória (resolve CanvasKit CORS sem falhas)
        try:
            import requests, base64
            r = requests.get(file_identifier, timeout=3)
            if r.status_code == 200 and r.content:
                b64 = base64.b64encode(r.content).decode("ascii")
                _URL_TO_B64[file_identifier] = b64
                return b64
        except Exception:
            pass
        return None

    storage = get_storage_service()
    # 1. Tenta pelo caminho físico padrão de upload
    try:
        phys_path = storage.get_physical_path(file_identifier)
        if phys_path.exists() and phys_path.is_file():
            with open(phys_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        pass

    # 2. Tenta como caminho direto no disco
    try:
        p = Path(file_identifier)
        if p.exists() and p.is_file():
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        pass

    # 3. Tenta dentro de ASSETS_DIR / uploads / filename
    try:
        from app.config import UPLOADS_DIR
        cand = UPLOADS_DIR / Path(file_identifier).name
        if cand.exists() and cand.is_file():
            with open(cand, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        pass

    return None


def get_storage_service() -> StorageService:
    """Fábrica para instanciar o serviço de armazenamento configurado."""
    import app.config as cfg
    backend = os.getenv("ECOBOUNTY_STORAGE_BACKEND", cfg.STORAGE_BACKEND).lower()
    if backend in ("catbox", "cat"):
        return CatboxStorageService()
    if backend in ("firebase", "gcp", "google"):
        return FirebaseStorageService()
    if backend == "azure" and AZURE_STORAGE_CONNECTION_STRING:
        return AzureBlobStorageService()
    return LocalStorageService()


_UPLOAD_SERVER_STARTED = False

# ---------------------------------------------------------------------------
# ESTADO EM TEMPO REAL ISOLADO POR DISPOSITIVO (cid = Client ID)
#
# Cada navegador/celular gera um identificador próprio (cid) e o envia em todas as
# chamadas ao servidor auxiliar. Ações pendentes, fotos, GPS, seleção de missão e
# resultado do login Google ficam em "gavetas" separadas por cid, de modo que um
# dispositivo NUNCA recebe eventos de outro.
#
# cid vazio ("") representa o modo legado de usuário único (execução local simples):
# nesse caso, todos os ouvintes sem cid continuam recebendo os eventos.
# ---------------------------------------------------------------------------
_STATE_LOCK = threading.RLock()
_PENDING_ACTIONS: Dict[str, tuple] = {}
_LATEST_PHOTOS: Dict[str, Optional[str]] = {}
_PHOTO_LISTENERS: list = []      # lista de (cid, callback)
_LOCATION_LISTENERS: list = []   # lista de (cid, callback)
_BOUNTY_LISTENERS: list = []     # lista de (cid, callback)
_GOOGLE_AUTH_RESULTS: Dict[str, Dict[str, Any]] = {}


def get_client_id(page) -> str:
    """Obtém o identificador do dispositivo (?cid=...) da sessão Flet; vazio se ausente."""
    if page is None:
        return ""
    cached = getattr(page, "_ecobounty_cid", None)
    if cached:
        return str(cached)

    cid = ""
    # 1. Tenta via page.query (mocks de teste ou QueryString já inicializada)
    try:
        q = getattr(page, "query", None)
        if q is not None:
            if callable(q) and getattr(q, "url", None) is None and getattr(page, "url", None):
                try:
                    q()
                except Exception:
                    pass
            val = q.get("cid")
            if val:
                cid = str(val)
    except Exception:
        pass

    # 2. Tenta extrair diretamente de page.route (ex.: '/?cid=c4054...')
    if not cid:
        try:
            import urllib.parse
            route = str(getattr(page, "route", "") or "")
            if "cid=" in route:
                qs = route.split("?", 1)[1] if "?" in route else route
                parsed = urllib.parse.parse_qs(qs)
                if "cid" in parsed and parsed["cid"]:
                    cid = str(parsed["cid"][0])
        except Exception:
            pass

    # 3. Tenta via page.client_storage (WebSocket direto com o localStorage do navegador)
    if not cid and page.__class__.__name__ == "Page" and hasattr(page, "client_storage"):
        try:
            cs_val = page.client_storage.get("ecobounty_cid")
            if cs_val and isinstance(cs_val, str):
                cid = cs_val.strip().strip('"')
        except Exception:
            pass

    if cid:
        try:
            setattr(page, "_ecobounty_cid", cid)
        except Exception:
            pass
    return cid


def _add_listener(registry: list, callback, cid: str) -> None:
    with _STATE_LOCK:
        if not any(cb == callback and c == (cid or "") for c, cb in registry):
            registry.append((cid or "", callback))


def _remove_listener(registry: list, callback) -> None:
    with _STATE_LOCK:
        registry[:] = [(c, cb) for c, cb in registry if cb != callback]


def _matching_listeners(registry: list, cid: str) -> list:
    """Ouvintes que devem receber um evento do dispositivo `cid`."""
    with _STATE_LOCK:
        if not cid:
            return [cb for _, cb in registry]  # modo legado: notifica todos
        return [cb for c, cb in registry if c == cid or c == ""]


def set_pending_action(action: str, data: Optional[dict] = None, cid: str = ""):
    """Define uma ação a ser executada no navegador (ex: 'request_gps', 'open_camera')."""
    with _STATE_LOCK:
        _PENDING_ACTIONS[cid or ""] = (action, data or {})


def pop_pending_action(cid: str = "") -> tuple:
    """Consome a ação pendente do navegador do dispositivo `cid`."""
    with _STATE_LOCK:
        act, data = _PENDING_ACTIONS.pop(cid or "", (None, {}))
        if act is None and cid and "" in _PENDING_ACTIONS:
            act, data = _PENDING_ACTIONS.pop("", (None, {}))
    return act, data


def register_photo_listener(callback, cid: str = ""):
    """Registra uma função callback a ser chamada quando uma nova foto for enviada."""
    _add_listener(_PHOTO_LISTENERS, callback, cid)


def unregister_photo_listener(callback):
    """Remove o callback de nova foto."""
    _remove_listener(_PHOTO_LISTENERS, callback)


def register_location_listener(callback, cid: str = ""):
    """Registra um callback a ser chamado quando o navegador enviar novas coordenadas de GPS."""
    _add_listener(_LOCATION_LISTENERS, callback, cid)


def unregister_location_listener(callback):
    """Remove o callback de localização."""
    _remove_listener(_LOCATION_LISTENERS, callback)


def register_bounty_listener(callback, cid: str = ""):
    """Registra um callback a ser chamado quando o usuário seleciona um bounty no mapa interativo."""
    _add_listener(_BOUNTY_LISTENERS, callback, cid)


def unregister_bounty_listener(callback):
    """Remove o callback de seleção de bounty."""
    _remove_listener(_BOUNTY_LISTENERS, callback)


def notify_bounty_selected(bounty_id: int, cid: str = ""):
    """Notifica os ouvintes (apenas do mesmo dispositivo) da seleção de uma missão no mapa."""
    for cb in _matching_listeners(_BOUNTY_LISTENERS, cid):
        try:
            cb(bounty_id)
        except Exception:
            pass


def get_latest_captured_photo(cid: str = "") -> Optional[str]:
    with _STATE_LOCK:
        return _LATEST_PHOTOS.get(cid or "")


def set_latest_captured_photo(path: str, cid: str = ""):
    with _STATE_LOCK:
        _LATEST_PHOTOS[cid or ""] = path
    for cb in _matching_listeners(_PHOTO_LISTENERS, cid):
        try:
            cb(path)
        except Exception:
            pass


def notify_location_update(lat: float, lng: float, cid: str = ""):
    # O GeoService é um singleton global: só é atualizado no modo legado (sem cid),
    # para que a posição de um usuário não vaze para a sessão de outro.
    if not cid:
        try:
            from app.services.geo_service import get_geo_service
            get_geo_service().update_from_gps(lat, lng)
        except Exception:
            pass
    for cb in _matching_listeners(_LOCATION_LISTENERS, cid):
        try:
            cb(lat, lng)
        except Exception:
            pass


_GOOGLE_AUTH_LOCK = threading.Lock()


def set_google_auth_result(data: Dict[str, Any], cid: str = "") -> None:
    """Registra o resultado da autenticação Google recebido pelo navegador do dispositivo `cid`."""
    with _GOOGLE_AUTH_LOCK:
        _GOOGLE_AUTH_RESULTS[cid or ""] = data


def pop_google_auth_result(cid: str = "") -> Optional[Dict[str, Any]]:
    """Recupera e consome o resultado pendente da autenticação Google do dispositivo `cid`."""
    with _GOOGLE_AUTH_LOCK:
        res = _GOOGLE_AUTH_RESULTS.pop(cid or "", None)
        if res is None and not cid and len(_GOOGLE_AUTH_RESULTS) == 1:
            only_key = next(iter(_GOOGLE_AUTH_RESULTS))
            res = _GOOGLE_AUTH_RESULTS.pop(only_key, None)
        elif res is None and cid and "" in _GOOGLE_AUTH_RESULTS:
            res = _GOOGLE_AUTH_RESULTS.pop("", None)
        return res


def start_upload_server(port: int = 8552) -> None:
    """Inicia um servidor HTTP em background para receber fotos, coordenadas e auth em tempo real."""
    global _UPLOAD_SERVER_STARTED
    if _UPLOAD_SERVER_STARTED:
        return
    import http.server
    import json
    import socketserver
    import sys
    import threading
    import urllib.parse

    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

        def handle_error(self, request, client_address):
            exc_type, exc_val, _ = sys.exc_info()
            # Silencia desconexões abruptas normais do navegador Windows (WinError 10053/10054/BrokenPipe)
            if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                return
            super().handle_error(request, client_address)

    class UploadHandler(http.server.BaseHTTPRequestHandler):
        def handle_one_request(self):
            try:
                super().handle_one_request()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                self.close_connection = True

        def _safe_write(self, data: bytes):
            try:
                self.wfile.write(data)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                self.close_connection = True

        def _send_cors_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def do_OPTIONS(self):
            try:
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Access-Control-Max-Age", "86400")
                self.end_headers()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass

        def _cid(self) -> str:
            """Identificador do dispositivo que originou a requisição (?cid=...)."""
            try:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                return (qs.get("cid", [""])[0] or "")[:64]
            except Exception:
                return ""

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            cid = self._cid()
            if parsed.path == "/location":
                qs = urllib.parse.parse_qs(parsed.query)
                lat_raw = qs.get("lat", [None])[0]
                lng_raw = qs.get("lng", [None])[0]
                if lat_raw and lng_raw:
                    try:
                        lat, lng = float(lat_raw), float(lng_raw)
                        notify_location_update(lat, lng, cid)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._send_cors_headers()
                        self.end_headers()
                        self._safe_write(json.dumps({"success": True, "lat": lat, "lng": lng}).encode("utf-8"))
                        return
                    except Exception:
                        pass

            if parsed.path == "/select_bounty":
                qs = urllib.parse.parse_qs(parsed.query)
                b_id = qs.get("id", [None])[0]
                if b_id:
                    try:
                        notify_bounty_selected(int(b_id), cid)
                    except Exception:
                        pass
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self._safe_write(json.dumps({"success": True, "id": b_id}).encode("utf-8"))
                return

            if parsed.path == "/action":
                act, act_data = pop_pending_action(cid)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self._safe_write(json.dumps({"action": act, "data": act_data}).encode("utf-8"))
                return

            if parsed.path == "/latest_photo":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self._safe_write(json.dumps({"latest_photo": get_latest_captured_photo(cid)}).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self._safe_write(b'{"status":"ok"}')

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            cid = self._cid()
            if parsed.path.startswith("/google_auth_callback"):
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    data = json.loads(body)
                    set_google_auth_result(data, cid)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self._safe_write(b'{"status":"ok"}')
                    return
                except Exception:
                    pass

            if parsed.path.startswith("/upload"):
                try:
                    qs = urllib.parse.parse_qs(parsed.query)
                    lat_str = qs.get("lat", [None])[0]
                    lng_str = qs.get("lng", [None])[0]
                    if lat_str and lng_str:
                        try:
                            notify_location_update(float(lat_str), float(lng_str), cid)
                        except Exception:
                            pass
                    length = int(self.headers.get("Content-Length", 0))
                    data = self.rfile.read(length) if length > 0 else b""
                    if data:
                        storage = get_storage_service()
                        saved_path = storage.save_image(data, "jpg")
                        filename = Path(saved_path).name if not saved_path.startswith("http") else saved_path.split("/")[-1]
                        set_latest_captured_photo(saved_path, cid)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._send_cors_headers()
                        self.end_headers()
                        resp = json.dumps({"success": True, "filename": filename, "path": saved_path, "url": saved_path})
                        self._safe_write(resp.encode("utf-8"))
                        return
                except Exception:
                    pass

            if parsed.path.startswith("/location"):
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    data = json.loads(body)
                    lat = float(data.get("lat"))
                    lng = float(data.get("lng"))
                    notify_location_update(lat, lng, cid)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self._safe_write(json.dumps({"success": True, "lat": lat, "lng": lng}).encode("utf-8"))
                    return
                except Exception:
                    pass

            self.send_response(400)
            self._send_cors_headers()
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server_created = False
    httpd_instance = None
    for host in ("0.0.0.0", "localhost", "127.0.0.1"):
        try:
            httpd_instance = ReusableTCPServer((host, port), UploadHandler)
            server_created = True
            break
        except Exception:
            continue

    if server_created and httpd_instance:
        def run():
            try:
                httpd_instance.serve_forever()
            except Exception:
                pass

        t = threading.Thread(target=run, daemon=True)
        t.start()
        _UPLOAD_SERVER_STARTED = True

