"""Configuração do Firebase / Google Cloud Firestore para o EcoBounty.

Projeto: ecobounty-9d250
Console: https://console.firebase.google.com/project/ecobounty-9d250/firestore/databases/-default-/data?hl=pt-br
"""
import importlib
import os
from typing import Any, Optional

try:
    firebase_admin = importlib.import_module("firebase_admin")
    credentials = importlib.import_module("firebase_admin.credentials")
    firestore = importlib.import_module("firebase_admin.firestore")
except Exception:
    firebase_admin = None
    credentials = None
    firestore = None

# Configurações do Firebase Web App / Projeto
FIREBASE_CONFIG = {
    "apiKey": "YOUR_GOOGLE_CLOUD_OR_FIREBASE_API_KEY",
    "authDomain": "ecobounty-9d250.firebaseapp.com",
    "projectId": "ecobounty-9d250",
    "storageBucket": "ecobounty-9d250.firebasestorage.app",
    "messagingSenderId": "497537080035",
    "appId": "1:497537080035:web:a403e448d9093feb1203d6",
    "measurementId": "G-KXRY4KB64S",
}

PROJECT_ID = FIREBASE_CONFIG["projectId"]
_firebase_app: Optional[Any] = None
_firestore_db = None


def get_firebase_app() -> Any:
    """Inicializa ou retorna a aplicação Firebase Admin ativa."""
    global _firebase_app
    if _firebase_app is None:
        try:
            _firebase_app = firebase_admin.get_app()
        except ValueError:
            from pathlib import Path
            base_dir = Path(__file__).resolve().parent
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not cred_path or not os.path.exists(cred_path):
                render_secrets = Path("/etc/secrets")
                secret_files = list(render_secrets.glob("*firebase-adminsdk*.json")) + [
                    render_secrets / "serviceAccountKey.json",
                    render_secrets / "service_account.json",
                ] if render_secrets.exists() else []
                candidates = [
                    base_dir / "serviceAccountKey.json",
                    base_dir / "service_account.json",
                    *list(base_dir.glob("*firebase-adminsdk*.json")),
                    *secret_files,
                ]
                for c in candidates:
                    if c.exists():
                        cred_path = str(c)
                        break

            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(str(cred_path))
                _firebase_app = firebase_admin.initialize_app(
                    cred,
                    {
                        "projectId": PROJECT_ID,
                        "storageBucket": FIREBASE_CONFIG["storageBucket"],
                    },
                )
            else:
                _firebase_app = firebase_admin.initialize_app(
                    options={
                        "projectId": PROJECT_ID,
                        "storageBucket": FIREBASE_CONFIG["storageBucket"],
                    }
                )
    return _firebase_app


def get_firestore_db():
    """Retorna o cliente do Cloud Firestore para o banco de dados ecobounty-9d250."""
    global _firestore_db
    if _firestore_db is None:
        get_firebase_app()
        _firestore_db = firestore.client()
    return _firestore_db
