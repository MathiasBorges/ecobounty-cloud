"""Configurações e parâmetros do EcoBounty.

Suporta execução local-first (custo zero) com integração nativa ao Google Cloud Platform
(Firebase Cloud Firestore, Firebase Storage, Google Cloud Vision e Google Auth).
"""
import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
ASSETS_DIR = BASE_DIR / "assets"
UPLOADS_DIR = ASSETS_DIR / "uploads"

# Carrega variáveis de ambiente do .env nativamente (sem dependência externa)
env_path = PROJECT_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, val = stripped.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass

# Garante que os diretórios essenciais existam
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Banco de dados local (SQLite embutido)
DB_PATH = os.getenv("ECOBOUNTY_DB_PATH", str(PROJECT_DIR / "ecobounty.db"))

# Coordenadas padrão (Maceió - AL, conforme especificação)
MACEIO_CENTER_LAT = -9.665
MACEIO_CENTER_LNG = -35.735
DEFAULT_USER_LAT = -9.668
DEFAULT_USER_LNG = -35.735

# Raio máximo permitido para check-in no local (em metros)
MAX_CHECKIN_RADIUS_METERS = 50.0

# Raio mínimo para detecção de duplicidade em denúncias (em metros)
MIN_DUPLICATE_RADIUS_METERS = 20.0

# Modo de simulação/apresentação (permite check-in instantâneo sem necessidade de deslocamento físico a pé)
SIMULATION_MODE = os.getenv("ECOBOUNTY_SIMULATION_MODE", "true").lower() in ("true", "1", "yes")

# Configuração da Google Maps Platform
GOOGLE_MAPS_API_KEY = os.getenv(
    "GOOGLE_MAPS_API_KEY",
    "",
)

# Chaveamento de Serviços de Armazenamento: "catbox" (padrão real), "firebase" ou "local"
STORAGE_BACKEND = os.getenv("ECOBOUNTY_STORAGE_BACKEND", "catbox")

# Chaveamento de Visão Computacional / Auditoria: "gemini" (padrão real), "google" ou "local"
VISION_BACKEND = os.getenv("ECOBOUNTY_VISION_BACKEND", "gemini")

# Configuração do Catbox (Hospedagem Permanente e Rápida de Imagens - https://catbox.moe)
# userhash é o token da conta (User Hash no painel da conta em catbox.moe).
CATBOX_USERHASH = os.getenv("CATBOX_USERHASH", "")

# Configuração do Google Gemini API (Google AI Studio Free Tier - https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
)

# Pool de modelos Google Gemini com suporte multimodal de visão e failover automático
GEMINI_MODELS_POOL = [
    "gemini-1.5-flash",       # Padrão estável: Multimodal Vision GA, gratuito no AI Studio
    "gemini-2.0-flash",       # Nova geração rápida e precisa
    "gemini-2.0-flash-lite",  # Ultra-rápido para baixa latência
    "gemini-1.5-flash-8b",    # Alta vazão para requisições frequentes
    "gemini-1.5-pro",         # Máxima capacidade de raciocínio
]
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", GEMINI_MODELS_POOL[0])

# Configurações do Google Cloud Platform & Firebase (Projeto ecobounty-9d250)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ecobounty-9d250")
FIREBASE_STORAGE_BUCKET = os.getenv(
    "FIREBASE_STORAGE_BUCKET", "ecobounty-9d250.firebasestorage.app"
)
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN", "ecobounty-9d250.firebaseapp.com")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# Configurações do Mercado Pago (Modo Sandbox / Pix & Transferências)
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY", "")
MERCADOPAGO_SANDBOX = os.getenv("MERCADOPAGO_SANDBOX", "true").lower() in ("true", "1", "yes")

# Configurações opcionais legadas para compatibilidade
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "ecobounty-uploads")
AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT", "")
AZURE_VISION_KEY = os.getenv("AZURE_VISION_KEY", "")

# Configuração do Servidor Web Local (0.0.0.0 para acesso tanto no PC quanto no celular na mesma rede)
SERVER_HOST = os.getenv("ECOBOUNTY_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("ECOBOUNTY_PORT", "8550"))
