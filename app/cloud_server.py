"""Ponto de entrada para hospedagem em nuvem (Render, Railway, Fly.io etc.).

Provedores de nuvem expõem UMA única porta pública (variável de ambiente PORT), mas o
EcoBounty usa dois servidores internos:

  - Flet (fletd) ........ 127.0.0.1:8550  -> interface, WebSocket /ws, arquivos estáticos
  - Servidor auxiliar ... 127.0.0.1:8552  -> GPS, câmera, login Google, seleção de missão

Este módulo sobe os dois e coloca na frente um proxy reverso (aiohttp) na porta pública:

  /ecoapi/*  -> servidor auxiliar (8552)   [prefixo removido]
  /ws        -> WebSocket do Flet (8550)
  demais     -> Flet (8550)

Execução:  python -m app.cloud_server
"""
import asyncio
import os
import sys
import threading
from pathlib import Path

# Modo nuvem: desativa detecção de localização pelo IP do servidor (seria o do datacenter)
os.environ.setdefault("ECOBOUNTY_CLOUD", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiohttp
from aiohttp import web

FLET_PORT = 8550
HELPER_PORT = 8552
PUBLIC_PORT = int(os.getenv("PORT", "10000"))

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
    "trailers", "transfer-encoding", "upgrade", "content-length", "content-encoding", "host",
}


def _clean_headers(headers) -> dict:
    return {k: v for k, v in headers.items() if k.lower() not in _HOP_BY_HOP}


async def _proxy_http(request: web.Request, target_base: str, path: str) -> web.StreamResponse:
    url = f"{target_base}{path}"
    if request.query_string:
        url += f"?{request.query_string}"
    headers = _clean_headers(request.headers)
    headers.pop("Accept-Encoding", None)
    body = await request.read()
    try:
        async with request.app["session"].request(
            request.method, url, headers=headers, data=body or None, allow_redirects=False
        ) as resp:
            payload = await resp.read()
            return web.Response(body=payload, status=resp.status, headers=_clean_headers(resp.headers))
    except aiohttp.ClientError as exc:
        return web.Response(status=502, text=f"Servidor interno indisponível: {exc}")


async def helper_handler(request: web.Request) -> web.StreamResponse:
    """/ecoapi/<rota> -> servidor auxiliar (remove o prefixo /ecoapi)."""
    return await _proxy_http(request, f"http://127.0.0.1:{HELPER_PORT}", "/" + request.match_info["tail"])


async def websocket_handler(request: web.Request) -> web.StreamResponse:
    """Encaminha o WebSocket do Flet (cliente <-> fletd) nos dois sentidos."""
    ws_client = web.WebSocketResponse(heartbeat=25)
    await ws_client.prepare(request)
    target = f"http://127.0.0.1:{FLET_PORT}{request.path}"
    if request.query_string:
        target += f"?{request.query_string}"
    async with request.app["session"].ws_connect(target, max_msg_size=0) as ws_server:

        async def client_to_server():
            async for msg in ws_client:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await ws_server.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await ws_server.send_bytes(msg.data)
                else:
                    break

        async def server_to_client():
            async for msg in ws_server:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await ws_client.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await ws_client.send_bytes(msg.data)
                else:
                    break

        tasks = [asyncio.ensure_future(client_to_server()), asyncio.ensure_future(server_to_client())]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in tasks:
            t.cancel()
    await ws_client.close()
    return ws_client


async def flet_handler(request: web.Request) -> web.StreamResponse:
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await websocket_handler(request)
    return await _proxy_http(request, f"http://127.0.0.1:{FLET_PORT}", request.path)


_ASSETLINKS_JSON = """[
  {
    "relation": [
      "delegate_permission/common.handle_all_urls",
      "delegate_permission/common.use_as_origin"
    ],
    "target": {
      "namespace": "android_app",
      "package_name": "com.onrender.ecobounty_app.twa",
      "sha256_cert_fingerprints": [
        "4C:AD:EC:1A:91:81:42:ED:B8:8C:89:B2:39:73:5F:4B:C1:A2:AF:24:CC:F6:D3:D4:EA:A8:96:FD:E6:71:96:92"
      ]
    }
  }
]"""


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def assetlinks_handler(request: web.Request) -> web.Response:
    """Digital Asset Links oficial do Android TWA para tela cheia nativa e delegação de GPS."""
    return web.Response(text=_ASSETLINKS_JSON, content_type="application/json")


async def _serve_proxy() -> None:
    app = web.Application(client_max_size=25 * 1024 * 1024)
    app["session"] = aiohttp.ClientSession(auto_decompress=True)
    app.router.add_get("/healthz", health_handler)
    app.router.add_get("/.well-known/assetlinks.json", assetlinks_handler)
    app.router.add_route("*", "/ecoapi/{tail:.*}", helper_handler)
    app.router.add_route("*", "/{tail:.*}", flet_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PUBLIC_PORT).start()
    print(f"🌐 Proxy público ativo na porta {PUBLIC_PORT}", flush=True)
    await asyncio.Event().wait()


def _run_proxy_thread() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_serve_proxy())


def run() -> None:
    import flet as ft

    from app.config import ASSETS_DIR, UPLOADS_DIR
    from app.main import main
    from app.services.storage_service import start_upload_server

    start_upload_server(HELPER_PORT)
    threading.Thread(target=_run_proxy_thread, daemon=True).start()

    print("🌱 EcoBounty (modo nuvem) iniciando...", flush=True)
    # host="*": vincula o fletd na porta interna; view=None: não tenta abrir navegador no servidor
    ft.app(
        target=main,
        port=FLET_PORT,
        host="*",
        view=None,
        assets_dir=str(ASSETS_DIR),
        upload_dir=str(UPLOADS_DIR),
    )


if __name__ == "__main__":
    run()

