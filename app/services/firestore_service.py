"""Serviço de Integração Completo com o Google Cloud Firestore (Firebase).

Gerencia a gravação, consulta e sincronização em tempo real das coleções:
- 'bounties': missões de limpeza e denúncias ambientais
- 'users': perfis de coletores, cidadãos e administradores (incluindo Google Auth)
- 'transactions': histórico contábil, chaves de idempotência e repasses financeiros
- 'history': histórico de missões finalizadas

Suporta autenticação por Conta de Serviço (Firebase Admin SDK) e REST API v1
com fallback local-first e leitura/escrita não-bloqueante.
"""
import json
import logging
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.config import GCP_PROJECT_ID, PROJECT_DIR, SIMULATION_MODE
from app.models.bounty import Bounty
from app.models.transaction import HistoryItem, Transaction
from app.models.user import User

logger = logging.getLogger(__name__)

PROJECT_ID = GCP_PROJECT_ID or "ecobounty-9d250"
API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "YOUR_GOOGLE_CLOUD_OR_FIREBASE_API_KEY")
REST_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"


class FirestoreService:
    _instance: Optional["FirestoreService"] = None

    def __init__(self):
        self.project_id = PROJECT_ID
        self.api_key = API_KEY
        self._admin_db = None
        self._local_docs: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._init_admin_sdk()

    @classmethod
    def get_instance(cls) -> "FirestoreService":
        if cls._instance is None:
            cls._instance = FirestoreService()
        return cls._instance

    def _find_service_account_path(self) -> Optional[Path]:
        """Localiza arquivo de chave de conta de serviço no projeto."""
        env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_cred and Path(env_cred).exists():
            return Path(env_cred)

        render_secrets = Path("/etc/secrets")
        secret_files = list(render_secrets.glob("*firebase-adminsdk*.json")) + [
            render_secrets / "serviceAccountKey.json",
            render_secrets / "service_account.json",
        ] if render_secrets.exists() else []

        candidates = [
            PROJECT_DIR / "serviceAccountKey.json",
            PROJECT_DIR / "service_account.json",
            PROJECT_DIR / "firebase_credentials.json",
            PROJECT_DIR / "firebase-service-account.json",
            *list(PROJECT_DIR.glob("*firebase-adminsdk*.json")),
            *secret_files,
        ]
        for p in candidates:
            if p.exists():
                return p

        # Busca recursiva por qualquer JSON com "type": "service_account"
        try:
            for p in PROJECT_DIR.glob("*.json"):
                if "serviceaccount" in p.name.lower() or "ecobounty" in p.name.lower():
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            content = json.load(f)
                            if content.get("type") == "service_account":
                                return p
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _init_admin_sdk(self):
        """Inicializa o Firebase Admin SDK caso a chave de conta de serviço esteja presente."""
        try:
            import importlib
            firebase_admin = importlib.import_module("firebase_admin")
            credentials = importlib.import_module("firebase_admin.credentials")
            firestore = importlib.import_module("firebase_admin.firestore")

            cred_path = self._find_service_account_path()
            if cred_path:
                try:
                    app = firebase_admin.get_app()
                except ValueError:
                    cred = credentials.Certificate(str(cred_path))
                    app = firebase_admin.initialize_app(
                        cred,
                        {
                            "projectId": self.project_id,
                            "storageBucket": f"{self.project_id}.firebasestorage.app",
                        },
                    )
                self._admin_db = firestore.client()
                logger.info("Firestore Admin SDK conectado com sucesso via Service Account.")
            else:
                self._admin_db = None
        except Exception as e:
            logger.debug(f"Admin SDK não inicializado (usando REST API): {e}")
            self._admin_db = None

    def is_admin_connected(self) -> bool:
        return self._admin_db is not None

    # ==========================================
    # Conversores bidirecionais REST Firestore
    # ==========================================
    @staticmethod
    def _to_firestore_value(val: Any) -> Dict[str, Any]:
        """Converte um tipo Python primitivo para o formato de campos do Firestore REST API."""
        if val is None:
            return {"nullValue": None}
        if isinstance(val, bool):
            return {"booleanValue": val}
        if isinstance(val, int):
            return {"integerValue": str(val)}
        if isinstance(val, float):
            return {"doubleValue": float(val)}
        if isinstance(val, dict):
            fields = {k: FirestoreService._to_firestore_value(v) for k, v in val.items()}
            return {"mapValue": {"fields": fields}}
        if isinstance(val, (list, tuple)):
            values = [FirestoreService._to_firestore_value(v) for v in val]
            return {"arrayValue": {"values": values}}
        return {"stringValue": str(val)}

    @staticmethod
    def _to_firestore_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: FirestoreService._to_firestore_value(v)
            for k, v in data.items()
            if v is not None
        }

    @staticmethod
    def _from_firestore_value(val_dict: Dict[str, Any]) -> Any:
        """Converte um campo do formato Firestore REST para tipo Python nativo."""
        if not isinstance(val_dict, dict):
            return val_dict
        if "stringValue" in val_dict:
            return val_dict["stringValue"]
        if "integerValue" in val_dict:
            return int(val_dict["integerValue"])
        if "doubleValue" in val_dict:
            return float(val_dict["doubleValue"])
        if "booleanValue" in val_dict:
            return bool(val_dict["booleanValue"])
        if "nullValue" in val_dict:
            return None
        if "mapValue" in val_dict:
            fields = val_dict.get("mapValue", {}).get("fields", {})
            return FirestoreService._from_firestore_fields(fields)
        if "arrayValue" in val_dict:
            values = val_dict.get("arrayValue", {}).get("values", [])
            return [FirestoreService._from_firestore_value(v) for v in values]
        return None

    @staticmethod
    def _from_firestore_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
        """Converte um mapa de campos Firestore REST para dicionário Python normal."""
        return {
            k: FirestoreService._from_firestore_value(v)
            for k, v in fields.items()
        }

    # ==========================================
    # Operações Genéricas de CRUD no Firestore
    # ==========================================
    def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """Salva ou atualiza um documento no Firestore (Admin SDK, REST API ou Cache Resiliente)."""
        # Sempre armazena no cache local em memória (local-first e offline-resilient)
        if collection not in self._local_docs:
            self._local_docs[collection] = {}
        self._local_docs[collection][str(doc_id)] = dict(data)

        if SIMULATION_MODE:
            return True

        if self._admin_db:
            try:
                self._admin_db.collection(collection).document(str(doc_id)).set(
                    data, merge=True
                )
                return True
            except Exception as e:
                logger.warning(f"Erro ao salvar via Admin SDK ({collection}/{doc_id}): {e}")

        # Fallback via REST API v1
        try:
            url = f"{REST_BASE_URL}/{collection}/{doc_id}?key={self.api_key}"
            payload = {"fields": self._to_firestore_fields(data)}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="PATCH",
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            logger.debug(f"Firestore REST API set_document ({collection}/{doc_id}): {e}")
            return True

    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Recupera um documento específico no Firestore pelo ID."""
        # 1. Verifica no cache local em memória
        if collection in self._local_docs and str(doc_id) in self._local_docs[collection]:
            d = dict(self._local_docs[collection][str(doc_id)])
            d["id"] = d.get("id", doc_id)
            return d

        if SIMULATION_MODE:
            return None

        # 2. Consulta Admin SDK se conectado
        if self._admin_db:
            try:
                doc = self._admin_db.collection(collection).document(str(doc_id)).get()
                if doc.exists:
                    d = doc.to_dict() or {}
                    d["id"] = d.get("id", doc.id)
                    return d
                return None
            except Exception as e:
                logger.warning(f"Erro ao obter documento via Admin SDK: {e}")

        # 3. Fallback via REST API v1
        try:
            url = f"{REST_BASE_URL}/{collection}/{doc_id}?key={self.api_key}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    raw = json.loads(resp.read().decode("utf-8"))
                    fields = raw.get("fields", {})
                    data = self._from_firestore_fields(fields)
                    data["id"] = data.get("id", doc_id)
                    return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            logger.debug(f"Firestore REST API get_document HTTP {e.code}: {e}")
        except Exception as e:
            logger.debug(f"Firestore REST API get_document Erro: {e}")
        return None

    def delete_document(self, collection: str, doc_id: str) -> bool:
        """Remove um documento do Firestore pelo ID."""
        if collection in self._local_docs:
            self._local_docs[collection].pop(str(doc_id), None)

        if SIMULATION_MODE:
            return True

        if self._admin_db:
            try:
                self._admin_db.collection(collection).document(str(doc_id)).delete()
                return True
            except Exception as e:
                logger.warning(f"Erro ao excluir documento via Admin SDK: {e}")

        # Fallback via REST API v1
        try:
            url = f"{REST_BASE_URL}/{collection}/{doc_id}?key={self.api_key}"
            req = urllib.request.Request(url, method="DELETE")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.debug(f"Firestore REST API delete_document: {e}")
            return True

    def get_collection(
        self,
        collection: str,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Recupera todos os documentos de uma coleção com filtros opcionais."""
        results: List[Dict[str, Any]] = []

        if collection in self._local_docs:
            for doc_id, d in self._local_docs[collection].items():
                item = dict(d)
                item["id"] = item.get("id", doc_id)
                if filters:
                    matches = True
                    for f_field, f_op, f_val in filters:
                        if f_op in ("==", "=") and item.get(f_field) != f_val:
                            matches = False
                            break
                    if not matches:
                        continue
                results.append(item)

        if SIMULATION_MODE or results:
            return results

        if self._admin_db:
            try:
                col_ref = self._admin_db.collection(collection)
                if filters:
                    for field, op, val in filters:
                        col_ref = col_ref.where(field, op, val)
                for doc in col_ref.stream():
                    d = doc.to_dict() or {}
                    d["id"] = d.get("id", doc.id)
                    results.append(d)
                return results
            except Exception as e:
                logger.warning(f"Erro ao listar coleção via Admin SDK: {e}")

        # Fallback via REST API v1
        try:
            url = f"{REST_BASE_URL}/{collection}?key={self.api_key}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    raw = json.loads(resp.read().decode("utf-8"))
                    docs = raw.get("documents", [])
                    for doc in docs:
                        name = doc.get("name", "")
                        doc_id = name.split("/")[-1] if "/" in name else ""
                        fields = doc.get("fields", {})
                        d = self._from_firestore_fields(fields)
                        d["id"] = d.get("id", doc_id)
                        if filters:
                            matches = True
                            for f_field, f_op, f_val in filters:
                                if f_op in ("==", "=") and d.get(f_field) != f_val:
                                    matches = False
                                    break
                            if not matches:
                                continue
                        results.append(d)
        except Exception as e:
            logger.debug(f"Firestore REST API get_collection: {e}")

        return results

    # ==========================================
    # Bounties (Missões e Denúncias)
    # ==========================================
    def _bounty_to_dict(self, bounty: Any) -> Dict[str, Any]:
        if hasattr(bounty, "__dict__"):
            return {
                "id": bounty.id,
                "title": bounty.title,
                "val": float(bounty.val),
                "dist": int(bounty.dist),
                "type": bounty.type,
                "dest": bounty.dest,
                "img": bounty.img,
                "lat": float(bounty.lat),
                "lng": float(bounty.lng),
                "icon": getattr(bounty, "icon", "trash"),
                "color": getattr(bounty, "color", "blue"),
                "sponsor": getattr(bounty, "sponsor", "Parceiro ESG Maceió"),
                "status": getattr(bounty, "status", "DISPONIVEL"),
                "assigned_user_id": getattr(bounty, "assigned_user_id", None),
                "current_phase": getattr(bounty, "current_phase", 0),
                "created_at": getattr(bounty, "created_at", None),
            }
        return dict(bounty)

    def _dict_to_bounty(self, d: Dict[str, Any]) -> Bounty:
        raw_id = d.get("id", 0)
        try:
            b_id = int(raw_id)
        except (ValueError, TypeError):
            b_id = abs(hash(str(raw_id))) % 1000000

        return Bounty(
            id=b_id,
            title=str(d.get("title", "Missão EcoBounty")),
            val=float(d.get("val", 25.0)),
            dist=int(d.get("dist", 0)),
            type=str(d.get("type", "Plástico")),
            dest=str(d.get("dest", "COOPLUM")),
            img=str(d.get("img", "/uploads/sample.jpg")),
            lat=float(d.get("lat", -9.665)),
            lng=float(d.get("lng", -35.735)),
            icon=str(d.get("icon", "trash")),
            color=str(d.get("color", "blue")),
            sponsor=str(d.get("sponsor", "Parceiro ESG Maceió")),
            status=str(d.get("status", "DISPONIVEL")),
            assigned_user_id=d.get("assigned_user_id"),
            current_phase=int(d.get("current_phase", 0)),
            created_at=d.get("created_at"),
        )

    def save_bounty(self, bounty: Any) -> bool:
        """Serializa e salva um Bounty no Firestore."""
        b_dict = self._bounty_to_dict(bounty)
        doc_id = str(b_dict["id"])
        return self.set_document("bounties", doc_id, b_dict)

    def save_bounty_async(self, bounty: Any):
        """Salva um Bounty em segundo plano (non-blocking)."""
        threading.Thread(target=self.save_bounty, args=(bounty,), daemon=True).start()

    def get_bounty(self, bounty_id: Union[int, str]) -> Optional[Bounty]:
        """Recupera um Bounty do Firestore pelo ID."""
        doc = self.get_document("bounties", str(bounty_id))
        if doc:
            return self._dict_to_bounty(doc)
        return None

    def get_all_bounties(self, status: Optional[str] = None) -> List[Bounty]:
        """Recupera todos os Bounties do Firestore, filtrando por status se especificado."""
        filters = [("status", "==", status)] if status else None
        docs = self.get_collection("bounties", filters=filters)
        return [self._dict_to_bounty(d) for d in docs]

    def update_bounty_status(
        self,
        bounty_id: int,
        status: str,
        assigned_user_id: Optional[int] = None,
        current_phase: Optional[int] = None,
    ) -> bool:
        """Atualiza status e dados de andamento de uma missão no Firestore."""
        data: Dict[str, Any] = {"status": status}
        if assigned_user_id is not None:
            data["assigned_user_id"] = assigned_user_id
        if current_phase is not None:
            data["current_phase"] = current_phase
        return self.set_document("bounties", str(bounty_id), data)

    def update_bounty_phase(self, bounty_id: int, phase: int, status: Optional[str] = None) -> bool:
        data: Dict[str, Any] = {"current_phase": phase}
        if status:
            data["status"] = status
        return self.set_document("bounties", str(bounty_id), data)

    # ==========================================
    # Users (Usuários, Coletores e Google Auth)
    # ==========================================
    def _user_to_dict(self, user: Any) -> Dict[str, Any]:
        if hasattr(user, "__dict__"):
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "cpf": user.cpf,
                "phone": user.phone,
                "balance": float(user.balance),
                "total_earnings": float(user.total_earnings),
                "waste_saved_kg": float(user.waste_saved_kg),
                "level_title": user.level_title,
                "role": getattr(user, "role", "COLETOR"),
                "created_at": getattr(user, "created_at", None),
                "google_id": getattr(user, "google_id", None),
            }
        d = dict(user)
        d.pop("password_hash", None)
        return d

    def _dict_to_user(self, d: Dict[str, Any]) -> User:
        raw_id = d.get("id", 0)
        try:
            u_id = int(raw_id)
        except (ValueError, TypeError):
            u_id = abs(hash(str(raw_id))) % 1000000

        user = User(
            id=u_id,
            name=str(d.get("name", "Usuário EcoBounty")),
            email=str(d.get("email", "")),
            cpf=str(d.get("cpf", "")),
            phone=str(d.get("phone", "")),
            password_hash=str(d.get("password_hash", "GOOGLE_AUTH")),
            balance=float(d.get("balance", 0.0)),
            total_earnings=float(d.get("total_earnings", 0.0)),
            waste_saved_kg=float(d.get("waste_saved_kg", 0.0)),
            level_title=str(d.get("level_title", "Nível 1 • Recruta Verde")),
            role=str(d.get("role", "COLETOR")),
            created_at=d.get("created_at"),
        )
        if "google_id" in d:
            setattr(user, "google_id", d["google_id"])
        return user

    def save_user(self, user: Any) -> bool:
        """Serializa e salva um User na coleção 'users' do Firestore."""
        u_dict = self._user_to_dict(user)
        doc_id = str(u_dict["id"])
        return self.set_document("users", doc_id, u_dict)

    def save_user_async(self, user: Any):
        """Salva um User em segundo plano (non-blocking)."""
        threading.Thread(target=self.save_user, args=(user,), daemon=True).start()

    def get_user(self, user_id: Union[int, str]) -> Optional[User]:
        """Recupera um User do Firestore pelo ID."""
        doc = self.get_document("users", str(user_id))
        if doc:
            return self._dict_to_user(doc)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Busca usuário pelo endereço de e-mail (case-insensitive)."""
        clean_email = email.strip().lower()
        docs = self.get_collection("users")
        for d in docs:
            if str(d.get("email", "")).strip().lower() == clean_email:
                return self._dict_to_user(d)
        return None

    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Busca usuário vinculado à conta Google Auth."""
        docs = self.get_collection("users")
        for d in docs:
            if d.get("google_id") == google_id:
                return self._dict_to_user(d)
        return None

    def update_user_balance(
        self,
        user_id: int,
        balance: float,
        total_earnings: float,
        waste_saved_kg: float,
    ) -> bool:
        """Atualiza saldos financeiros e impacto ambiental do usuário."""
        data = {
            "balance": float(balance),
            "total_earnings": float(total_earnings),
            "waste_saved_kg": float(waste_saved_kg),
        }
        return self.set_document("users", str(user_id), data)

    # ==========================================
    # Transactions (Transações e Carteira Digital)
    # ==========================================
    def save_transaction(self, tx: Any) -> bool:
        """Serializa e salva uma Transação financeira com idempotência."""
        if hasattr(tx, "__dict__"):
            t_dict = {
                "id": getattr(tx, "id", None),
                "user_id": getattr(tx, "user_id", None),
                "bounty_id": getattr(tx, "bounty_id", None),
                "amount": float(getattr(tx, "amount", 0.0)),
                "type": getattr(tx, "type", "CREDITO"),
                "idempotency_key": getattr(tx, "idempotency_key", ""),
                "created_at": getattr(tx, "created_at", None),
            }
        else:
            t_dict = dict(tx)

        doc_id = str(t_dict.get("idempotency_key") or t_dict.get("id"))
        return self.set_document("transactions", doc_id, t_dict)

    def save_transaction_async(self, tx: Any):
        threading.Thread(target=self.save_transaction, args=(tx,), daemon=True).start()

    def get_transactions_for_user(self, user_id: Union[int, str]) -> List[Transaction]:
        """Recupera transações do usuário no Firestore."""
        target_id = int(user_id) if str(user_id).isdigit() else user_id
        docs = self.get_collection("transactions")
        results: List[Transaction] = []
        for d in docs:
            if d.get("user_id") == target_id:
                results.append(
                    Transaction(
                        id=int(d.get("id", 0)),
                        user_id=int(d.get("user_id", 0)),
                        bounty_id=int(d.get("bounty_id", 0)),
                        type=str(d.get("type", "CREDITO")),
                        amount=float(d.get("amount", 0.0)),
                        idempotency_key=str(d.get("idempotency_key", "")),
                        created_at=d.get("created_at"),
                    )
                )
        return results

    # ==========================================
    # History (Histórico de Missões Concluídas)
    # ==========================================
    def save_history(self, item: Any) -> bool:
        """Salva item de histórico de missão concluída no Firestore."""
        if hasattr(item, "__dict__"):
            h_dict = {
                "id": getattr(item, "id", None),
                "user_id": getattr(item, "user_id", None),
                "title": getattr(item, "title", ""),
                "status": getattr(item, "status", "Concluído"),
                "amount": float(getattr(item, "amount", 0.0)),
                "date_label": getattr(item, "date_label", ""),
                "created_at": getattr(item, "created_at", None),
            }
        else:
            h_dict = dict(item)

        doc_id = str(h_dict.get("id") or f"hist_{h_dict.get('user_id')}_{h_dict.get('created_at')}")
        return self.set_document("history", doc_id, h_dict)

    def save_history_async(self, item: Any):
        threading.Thread(target=self.save_history, args=(item,), daemon=True).start()

    def get_history_for_user(self, user_id: Union[int, str]) -> List[HistoryItem]:
        """Recupera o histórico recente de missões de um coletor no Firestore."""
        target_id = int(user_id) if str(user_id).isdigit() else user_id
        docs = self.get_collection("history")
        results: List[HistoryItem] = []
        for d in docs:
            if d.get("user_id") == target_id:
                results.append(
                    HistoryItem(
                        id=int(d.get("id", 0)),
                        user_id=int(d.get("user_id", 0)),
                        title=str(d.get("title", "")),
                        status=str(d.get("status", "Concluído")),
                        amount=float(d.get("amount", 0.0)),
                        date_label=str(d.get("date_label", "")),
                        created_at=d.get("created_at"),
                    )
                )
        return results

    # ==========================================
    # Sincronização Local $\rightarrow$ Nuvem
    # ==========================================
    def sync_all_from_sqlite(self) -> Dict[str, int]:
        """Exporta todos os dados do banco local SQLite para as coleções do Firestore."""
        from app.database.connection import get_connection

        conn = get_connection()
        counts = {"bounties": 0, "users": 0, "transactions": 0, "history": 0}

        try:
            # Sincroniza Usuários
            users_rows = conn.execute("SELECT * FROM users").fetchall()
            for r in users_rows:
                u_data = dict(r)
                u_data.pop("password_hash", None)
                if self.set_document("users", str(u_data["id"]), u_data):
                    counts["users"] += 1

            # Sincroniza Bounties
            bounty_rows = conn.execute("SELECT * FROM bounties").fetchall()
            for r in bounty_rows:
                b_data = dict(r)
                if self.set_document("bounties", str(b_data["id"]), b_data):
                    counts["bounties"] += 1

            # Sincroniza Transações
            tx_rows = conn.execute("SELECT * FROM transactions").fetchall()
            for r in tx_rows:
                t_data = dict(r)
                doc_id = str(t_data.get("idempotency_key") or t_data["id"])
                if self.set_document("transactions", doc_id, t_data):
                    counts["transactions"] += 1

            # Sincroniza Histórico
            hist_rows = conn.execute("SELECT * FROM history").fetchall()
            for r in hist_rows:
                h_data = dict(r)
                doc_id = str(h_data["id"])
                if self.set_document("history", doc_id, h_data):
                    counts["history"] += 1

            logger.info(f"Sincronização Firestore concluída com sucesso: {counts}")
        except Exception as e:
            logger.error(f"Erro durante sincronização com Firestore: {e}")
        finally:
            conn.close()

        return counts


def get_firestore_service() -> FirestoreService:
    return FirestoreService.get_instance()
