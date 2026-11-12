"""Script para sincronizar os dados locais (SQLite) com o Cloud Firestore (Firebase).

Uso:
  python scripts/sync_firestore.py
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.firestore_service import get_firestore_service


def main():
    print("🔥 Iniciando sincronização com o Google Cloud Firestore...")
    svc = get_firestore_service()
    print(f"📌 Projeto: {svc.project_id}")
    print(f"🔑 Admin SDK Conectado: {'SIM (Service Account ativa)' if svc.is_admin_connected() else 'NÃO (usando REST API pública)'}")

    res = svc.sync_all_from_sqlite()
    print("✅ Sincronização finalizada com sucesso!")
    print(f"📊 Registros enviados: {res}")


if __name__ == "__main__":
    main()

