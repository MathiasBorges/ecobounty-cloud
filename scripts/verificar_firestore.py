"""Script de Verificação e Visualização dos Dados no Cloud Firestore.

Consulta diretamente o banco de dados na nuvem (ecobounty-9d250) e exibe os registros.

Uso:
  python scripts/verificar_firestore.py
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.firestore_service import get_firestore_service


def main():
    print("=" * 60)
    print("🔥 CONSULTANDO BANCO DE DADOS CLOUD FIRESTORE (ecobounty-9d250)")
    print("=" * 60)

    svc = get_firestore_service()
    if not svc._admin_db:
        print("❌ Admin SDK não inicializado. Verifique a chave serviceAccountKey.json.")
        return

    db = svc._admin_db

    # 1. Coleção Bounties (Missões)
    bounties_docs = list(db.collection("bounties").stream())
    print(f"\n📍 COLEÇÃO 'bounties' ({len(bounties_docs)} documentos):")
    print("-" * 60)
    for doc in bounties_docs[:10]:
        d = doc.to_dict()
        title = d.get("title", "Sem título")
        val = d.get("val", 0.0)
        status = d.get("status", "DISPONIVEL")
        lat = d.get("lat", 0.0)
        lng = d.get("lng", 0.0)
        print(f"  • [ID {doc.id:>2}] {title:<32} R$ {val:>6.2f} | Status: {status:<12} | GPS: ({lat:.4f}, {lng:.4f})")
    if len(bounties_docs) > 10:
        print(f"    ... e mais {len(bounties_docs) - 10} missões cadastradas.")

    # 2. Coleção Users (Usuários)
    users_docs = list(db.collection("users").stream())
    print(f"\n👤 COLEÇÃO 'users' ({len(users_docs)} documentos):")
    print("-" * 60)
    for doc in users_docs:
        d = doc.to_dict()
        name = d.get("name", "Sem nome")
        email = d.get("email", "")
        role = d.get("role", "COLETOR")
        balance = d.get("balance", 0.0)
        print(f"  • [ID {doc.id:>2}] {name:<25} ({email:<25}) | Perfil: {role:<10} | Saldo: R$ {balance:.2f}")

    # 3. Coleção Transactions (Transações)
    tx_docs = list(db.collection("transactions").stream())
    print(f"\n💳 COLEÇÃO 'transactions' ({len(tx_docs)} documentos):")
    print("-" * 60)
    for doc in tx_docs:
        d = doc.to_dict()
        desc = d.get("description", "Transação")
        amt = d.get("amount", 0.0)
        t_type = d.get("type", "CREDITO")
        print(f"  • [ID {doc.id}] {desc:<35} | {t_type}: R$ {amt:.2f}")

    print("\n" + "=" * 60)
    print("✅ Todos os dados acima estão salvos e sincronizados no Firestore!")
    print("🌐 Link Web: https://console.firebase.google.com/project/ecobounty-9d250/firestore/databases/-default-/data")
    print("=" * 60)


if __name__ == "__main__":
    main()

