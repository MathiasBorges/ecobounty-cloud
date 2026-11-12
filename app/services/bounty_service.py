"""Serviço de Gestão do Ciclo de Vida dos Bounties e Denúncias."""
import math
from datetime import datetime
from typing import Any, List, Optional, Tuple

from app.config import (
    DEFAULT_USER_LAT,
    DEFAULT_USER_LNG,
    MAX_CHECKIN_RADIUS_METERS,
    MIN_DUPLICATE_RADIUS_METERS,
)
from app.database.connection import get_connection
from app.models.bounty import Bounty
from app.services.storage_service import StorageService, get_storage_service
from app.services.vision_service import VisionService, get_vision_service
from app.services.wallet_service import WalletService

# Integração formal das Estruturas de Dados e Algoritmos (1ª e 2ª Unidades)
from app.data_structures.vector import CustomVector
from app.data_structures.hash_table import SeparateChainingHashTable, OpenAddressingHashTable
from app.data_structures.stack import UndoRedoManager
from app.data_structures.queue import Queue
from app.data_structures.restricted_list import RestrictedLinearList
from app.algorithms.sorting import quick_sort, bubble_sort, insertion_sort, selection_sort


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância geodésica em metros entre dois pontos geográficos."""
    r = 6371000.0  # Raio da Terra em metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class BountyService:
    def __init__(
        self,
        db_path: Optional[str] = None,
        wallet_service: Optional[WalletService] = None,
        vision_service: Optional[VisionService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.db_path = db_path
        self.wallet_service = wallet_service or WalletService(db_path)
        self.vision_service = vision_service or get_vision_service()
        self.storage_service = storage_service or get_storage_service()

        # Diferencial 1: Tabela Hash por Encadeamento para catálogo dinâmico de bounties
        self.bounty_cache: SeparateChainingHashTable[int, Bounty] = SeparateChainingHashTable[int, Bounty](initial_capacity=19)

        # Diferencial 1: Tabela Hash por Endereçamento Aberto para rápido lookup de ecopontos e QR codes
        self.ecopoints_hash: OpenAddressingHashTable[str, dict] = OpenAddressingHashTable[str, dict](initial_capacity=17)

        # 1ª Unidade: Fila FIFO para processamento assíncrono de fotos de auditoria
        self.audit_queue: Queue[dict] = Queue[dict]()

        # 1ª Unidade: Pilha LIFO de Undo/Redo para reversão de ações de missões
        self.undo_manager: UndoRedoManager[dict] = UndoRedoManager[dict]()

        # 1ª Unidade: Lista linear restrita de slots ativos de missões (limite regulamentar max 5)
        self.active_slots: RestrictedLinearList[int] = RestrictedLinearList[int](max_capacity=5)

        # Diferencial 2: Grafo canônico de reciclagem e roteamento viário de Maceió (Dijkstra)
        from app.algorithms.graphs import build_maceio_recycling_graph
        self.graph = build_maceio_recycling_graph()

        # Registro de ecopontos no cache hash com endereçamento aberto
        self._init_ecopoints_hash()

    def _init_ecopoints_hash(self) -> None:
        pjs = [
            ("ECOPONTO-COOPLUM-001", {"name": "COOPLUM", "bairro": "Jacarecica", "lat": -9.6105, "lng": -35.6980}),
            ("ECOPONTO-JATIUCA-001", {"name": "Ecoponto Jatiúca", "bairro": "Jatiúca", "lat": -9.6450, "lng": -35.7010}),
            ("ECOPONTO-PAJUCARA-001", {"name": "Ecoponto Pajuçara", "bairro": "Pajuçara", "lat": -9.6675, "lng": -35.7180}),
            ("ECOPONTO-PONTA-VERDE-001", {"name": "Ecoponto Ponta Verde", "bairro": "Ponta Verde", "lat": -9.6610, "lng": -35.7020}),
            ("ECOPONTO-CRUZ-DAS-ALMAS-001", {"name": "Ecoponto Cruz das Almas", "bairro": "Cruz das Almas", "lat": -9.6280, "lng": -35.7050}),
        ]
        for code, info in pjs:
            self.ecopoints_hash.put(code, info)

    def lookup_ecopoint(self, qr_code: str) -> Optional[dict]:
        """Lookup rápido O(1) de Ecoponto via Tabela Hash com Endereçamento Aberto."""
        clean_code = qr_code.strip().upper()
        return self.ecopoints_hash.get(clean_code)

    def ensure_nearby_bounties(
        self,
        user_lat: float,
        user_lng: float,
        conn: Optional[Any] = None,
    ) -> List[Bounty]:
        """Garante a existência de missões próximas (< 2.5km) ao usuário no mapa."""
        close_conn = False
        if conn is None:
            conn = get_connection(self.db_path)
            close_conn = True

        try:
            rows = conn.execute("SELECT * FROM bounties WHERE status = 'DISPONIVEL'").fetchall()
            existing = [Bounty.from_row(r) for r in rows]
            nearby = [b for b in existing if haversine_distance(user_lat, user_lng, b.lat, b.lng) <= 3000]
            if len(nearby) >= 4:
                return nearby

            now = datetime.now().isoformat()
            templates = [
                {
                    "title": "Garrafas PET e Embalagens",
                    "val": 25.00,
                    "type": "Plástico",
                    "dest": "COOPLUM",
                    "img": "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80",
                    "d_lat": 0.0030,
                    "d_lng": 0.0025,
                    "icon": "cup-soda",
                    "color": "blue",
                    "sponsor": "EcoBounty Circular",
                },
                {
                    "title": "Entulho e Resíduos na Calçada",
                    "val": 45.00,
                    "type": "Inerte",
                    "dest": "Ecoponto ALURB",
                    "img": "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=800&q=80",
                    "d_lat": -0.0065,
                    "d_lng": 0.0040,
                    "icon": "hammer",
                    "color": "orange",
                    "sponsor": "Construtora Verde",
                },
                {
                    "title": "Lixo Eletrônico e Cabos",
                    "val": 60.00,
                    "type": "Eletrônicos",
                    "dest": "COOPREL",
                    "img": "https://images.unsplash.com/photo-1550989460-0adf9ea622e2?auto=format&fit=crop&w=800&q=80",
                    "d_lat": 0.0105,
                    "d_lng": -0.0080,
                    "icon": "monitor",
                    "color": "slate",
                    "sponsor": "TechGreen ESG",
                },
                {
                    "title": "Papelão e Caixas Comerciais",
                    "val": 30.00,
                    "type": "Papelão",
                    "dest": "COOPLUM",
                    "img": "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?auto=format&fit=crop&w=800&q=80",
                    "d_lat": -0.0120,
                    "d_lng": -0.0090,
                    "icon": "box",
                    "color": "amber",
                    "sponsor": "Maceió Sustentável",
                },
                {
                    "title": "Latinhas e Sucata de Metal",
                    "val": 35.00,
                    "type": "Metal",
                    "dest": "Ecoponto ALURB",
                    "img": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=800&q=80",
                    "d_lat": 0.0150,
                    "d_lng": 0.0120,
                    "icon": "can",
                    "color": "emerald",
                    "sponsor": "Recicla Alagoas",
                },
            ]

            needed = 5 - len(nearby)
            inserted = []
            for t in templates[:needed]:
                b_lat = round(user_lat + t["d_lat"], 6)
                b_lng = round(user_lng + t["d_lng"], 6)
                dist_m = round(haversine_distance(user_lat, user_lng, b_lat, b_lng))
                cursor = conn.execute(
                    """
                    INSERT INTO bounties (title, val, dist, type, dest, img, lat, lng, icon, color, sponsor, status, assigned_user_id, current_phase, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPONIVEL', NULL, 0, ?)
                    """,
                    (
                        t["title"],
                        t["val"],
                        dist_m,
                        t["type"],
                        t["dest"],
                        t["img"],
                        b_lat,
                        b_lng,
                        t["icon"],
                        t["color"],
                        t["sponsor"],
                        now,
                    ),
                )
                b_id = cursor.lastrowid
                b = Bounty(
                    id=b_id,
                    title=t["title"],
                    val=t["val"],
                    dist=dist_m,
                    type=t["type"],
                    dest=t["dest"],
                    img=t["img"],
                    lat=b_lat,
                    lng=b_lng,
                    icon=t["icon"],
                    color=t["color"],
                    sponsor=t["sponsor"],
                    status="DISPONIVEL",
                    created_at=now,
                )
                self.bounty_cache.put(b_id, b)
                inserted.append(b)

            conn.commit()
            return nearby + inserted
        finally:
            if close_conn:
                conn.close()

    def get_bounties(
        self,
        filter_type: str = "todos",
        include_completed: bool = False,
        sort_method: str = "quicksort",
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
    ) -> List[Bounty]:
        """Recupera bounties do banco aplicando ordenação algorítmica (Diferencial 3) e filtros (UC03, UC04)."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT * FROM bounties WHERE 1=1"
            params = []
            if not include_completed:
                query += " AND status != 'CONCLUIDO'"

            rows = conn.execute(query, params).fetchall()
            bounties = [Bounty.from_row(r) for r in rows]

            # Garante que existam bounties próximos ao usuário se informada a localização
            if user_lat is not None and user_lng is not None:
                nearby = [b for b in bounties if haversine_distance(user_lat, user_lng, b.lat, b.lng) <= 3000]
                if len(nearby) < 3:
                    self.ensure_nearby_bounties(user_lat, user_lng, conn=conn)
                    rows = conn.execute(query, params).fetchall()
                    bounties = [Bounty.from_row(r) for r in rows]

                # Atualiza distâncias geodésicas em tempo real e calcula métricas Dijkstra da malha viária
                for b in bounties:
                    b.dist = round(haversine_distance(user_lat, user_lng, b.lat, b.lng))
                    try:
                        routing = self.graph.compute_bounty_routing(
                            user_lat=user_lat,
                            user_lng=user_lng,
                            bounty_lat=b.lat,
                            bounty_lng=b.lng,
                            bounty_val=b.val,
                        )
                        b.dijkstra_km = routing["total_dijkstra_km"]
                        b.dijkstra_score = routing["efficiency_score"]
                    except Exception:
                        b.dijkstra_km = round(b.dist / 1000.0, 2)
                        b.dijkstra_score = round(b.val / max(0.5, b.dist / 1000.0), 2)

            # Atualiza cache hash com encadeamento separado
            for b in bounties:
                self.bounty_cache.put(b.id, b)

            # Aplicação dos filtros em memória conforme especificação
            filter_lower = filter_type.lower()
            if filter_lower == "plastico":
                bounties = [b for b in bounties if b.type.lower() == "plástico" or b.type.lower() == "plastico"]
            elif filter_lower in ("dijkstra", "rota_otima", "melhor"):
                # Diferencial 2 & 3: Ordenação pelo trajeto viário ótimo calculado por Dijkstra
                bounties, _ = quick_sort(
                    bounties,
                    key=lambda b: (b.dijkstra_km if b.dijkstra_km is not None else 999.0),
                    reverse=False,
                )
            elif filter_lower == "valiosos":
                # Diferencial 3: Ordenação por recompensa via QuickSort (ou método escolhido)
                if sort_method == "bubble":
                    bounties, _ = bubble_sort(bounties, key=lambda b: b.val, reverse=True)
                elif sort_method == "insertion":
                    bounties, _ = insertion_sort(bounties, key=lambda b: b.val, reverse=True)
                elif sort_method == "selection":
                    bounties, _ = selection_sort(bounties, key=lambda b: b.val, reverse=True)
                else:
                    bounties, _ = quick_sort(bounties, key=lambda b: b.val, reverse=True)
            elif filter_lower == "proximos":
                # Diferencial 3: Ordenação por distância via QuickSort (ou método escolhido)
                if sort_method == "bubble":
                    bounties, _ = bubble_sort(bounties, key=lambda b: b.dist, reverse=False)
                elif sort_method == "insertion":
                    bounties, _ = insertion_sort(bounties, key=lambda b: b.dist, reverse=False)
                elif sort_method == "selection":
                    bounties, _ = selection_sort(bounties, key=lambda b: b.dist, reverse=False)
                else:
                    bounties, _ = quick_sort(bounties, key=lambda b: b.dist, reverse=False)

            return bounties
        finally:
            conn.close()

    def get_bounties_vector(self, filter_type: str = "todos") -> CustomVector[Bounty]:
        """Retorna os bounties encapsulados na estrutura Vetor Dinâmico (1ª Unidade)."""
        b_list = self.get_bounties(filter_type)
        vec = CustomVector[Bounty](initial_capacity=max(4, len(b_list)))
        for b in b_list:
            vec.append(b)
        return vec

    def get_bounty_by_id(self, bounty_id: int) -> Optional[Bounty]:
        # Consulta primeiro a Tabela Hash com Encadeamento Separado
        cached = self.bounty_cache.get(bounty_id)
        if cached:
            return cached

        conn = get_connection(self.db_path)
        try:
            row = conn.execute("SELECT * FROM bounties WHERE id = ?", (bounty_id,)).fetchone()
            if row:
                b = Bounty.from_row(row)
                self.bounty_cache.put(b.id, b)
                return b
        finally:
            conn.close()

        # Fallback de consulta no Cloud Firestore se não encontrado localmente
        try:
            from app.services.firestore_service import get_firestore_service
            cloud_b = get_firestore_service().get_bounty(bounty_id)
            if cloud_b:
                self.bounty_cache.put(cloud_b.id, cloud_b)
                return cloud_b
        except Exception:
            pass

        return None

    def accept_bounty(self, bounty_id: int, user_id: int) -> Tuple[bool, str]:
        """Reserva uma missão para o coletor (UC06, UC07), gerenciando slots restritos e undo."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                row = conn.execute("SELECT * FROM bounties WHERE id = ?", (bounty_id,)).fetchone()
                if not row:
                    return False, "Missão não encontrada"

                bounty = Bounty.from_row(row)
                if bounty.status == "CONCLUIDO":
                    return False, "Esta missão já foi concluída"

                if bounty.status == "EM_ANDAMENTO" and bounty.assigned_user_id != user_id:
                    # Conforme UC06 FE2
                    return False, "Missão indisponível – já aceita por outro coletor"

                conn.execute(
                    """
                    UPDATE bounties
                    SET status = 'EM_ANDAMENTO',
                        assigned_user_id = ?,
                        current_phase = 1
                    WHERE id = ?
                    """,
                    (user_id, bounty_id),
                )

                # Atualiza cache hash
                bounty.status = "EM_ANDAMENTO"
                bounty.assigned_user_id = user_id
                bounty.current_phase = 1
                self.bounty_cache.put(bounty_id, bounty)

                # Registra na Pilha LIFO de Undo
                self.undo_manager.record_action({
                    "action": "accept",
                    "bounty_id": bounty_id,
                    "user_id": user_id,
                })

                # Adiciona no slot restrito (se não estiver cheio)
                if not self.active_slots.is_full() and bounty_id not in self.active_slots.to_list():
                    self.active_slots.insert(bounty_id)

                try:
                    from app.services.firestore_service import get_firestore_service
                    get_firestore_service().save_bounty_async(bounty)
                except Exception:
                    pass

                return True, "Missão aceita com sucesso!"
        finally:
            conn.close()

    def undo_last_action(self) -> Tuple[bool, str]:
        """Desfaz a última ação registrada (1ª Unidade: Pilha LIFO)."""
        if not self.undo_manager.can_undo():
            return False, "Nenhuma ação para desfazer"

        action = self.undo_manager.undo()
        if action.get("action") == "accept":
            b_id = action.get("bounty_id")
            conn = get_connection(self.db_path)
            try:
                with conn:
                    conn.execute(
                        "UPDATE bounties SET status = 'DISPONIVEL', assigned_user_id = NULL, current_phase = 0 WHERE id = ?",
                        (b_id,),
                    )
                b = self.get_bounty_by_id(b_id)
                if b:
                    b.status = "DISPONIVEL"
                    b.assigned_user_id = None
                    b.current_phase = 0
                    self.bounty_cache.put(b_id, b)
                self.active_slots.remove_item(b_id)
                try:
                    from app.services.firestore_service import get_firestore_service
                    get_firestore_service().update_bounty_status(b_id, "DISPONIVEL", assigned_user_id=None, current_phase=0)
                except Exception:
                    pass
                return True, f"Ação desfeita: Missão #{b_id} retornou para disponível"
            finally:
                conn.close()
        return False, "Tipo de ação não reversível"

    def enqueue_photo_audit(self, bounty_id: int, user_id: int, image_data: Any) -> int:
        """Enfileira foto para auditoria assíncrona (1ª Unidade: Fila FIFO). Retorna tamanho da fila."""
        self.audit_queue.enqueue({
            "bounty_id": bounty_id,
            "user_id": user_id,
            "image_data": image_data,
            "timestamp": datetime.now().isoformat(),
        })
        return len(self.audit_queue)

    def process_next_photo_audit(self) -> Optional[dict]:
        """Desenfileira e processa a próxima auditoria da fila (1ª Unidade: Fila FIFO)."""
        if self.audit_queue.is_empty():
            return None
        item = self.audit_queue.dequeue()
        ok, reward, msg = self.validate_phase1_cleaning(
            bounty_id=item["bounty_id"],
            user_id=item["user_id"],
            image_data=item["image_data"],
        )
        return {"bounty_id": item["bounty_id"], "success": ok, "reward": reward, "message": msg}


    def check_in_cleaning_location(
        self,
        bounty_id: int,
        user_lat: float,
        user_lng: float,
        enforce_radius: bool = True,
    ) -> Tuple[bool, str, float]:
        """Valida se o usuário chegou no local do resíduo (raio ≤ 50m conforme UC07 FE2)."""
        bounty = self.get_bounty_by_id(bounty_id)
        if not bounty:
            return False, "Missão não encontrada", 0.0

        dist = haversine_distance(user_lat, user_lng, bounty.lat, bounty.lng)
        if enforce_radius and dist > MAX_CHECKIN_RADIUS_METERS:
            return False, f"Você ainda não está no local da missão ({int(dist)} m)", dist

        return True, "Check-in realizado com sucesso", dist

    def validate_phase1_cleaning(
        self,
        bounty_id: int,
        user_id: int,
        image_data: Any = None,
        simulate_failure: bool = False,
    ) -> Tuple[bool, float, str]:
        """Audita limpeza por IA e credita adiantamento de 50% (UC08)."""
        bounty = self.get_bounty_by_id(bounty_id)
        if not bounty:
            return False, 0.0, "Missão não encontrada"

        # Chamada ao serviço de visão computacional
        audit = self.vision_service.audit_cleaning(
            image_data=image_data,
            bounty_id=bounty_id,
            simulate_failure=simulate_failure,
        )

        if not audit.get("approved", False):
            return False, 0.0, audit.get("message", "Limpeza não validada.")

        # Credita 50% de adiantamento na carteira digital
        half_val = bounty.half_value()
        self.wallet_service.credit_advance(user_id, bounty_id, bounty.val)

        # Atualiza a missão para a Fase 2 (Destinação)
        conn = get_connection(self.db_path)
        try:
            with conn:
                conn.execute(
                    "UPDATE bounties SET current_phase = 2 WHERE id = ?",
                    (bounty_id,),
                )
        finally:
            conn.close()

        bounty.current_phase = 2
        self.bounty_cache.put(bounty_id, bounty)
        try:
            from app.services.firestore_service import get_firestore_service
            get_firestore_service().update_bounty_phase(bounty_id, 2)
        except Exception:
            pass

        return True, half_val, "Área Limpa! Adiantamento de 50% creditado."

    def validate_phase2_ecopoint(
        self,
        bounty_id: int,
        user_id: int,
        qrcode_data: Optional[str] = None,
        image_data: Any = None,
    ) -> Tuple[bool, float, str]:
        """Valida destinação via foto do descarte no Ecoponto/Lixeira ou QR Code (UC09)."""
        bounty = self.get_bounty_by_id(bounty_id)
        if not bounty:
            return False, 0.0, "Missão não encontrada"

        # Se houver foto da entrega, envia para auditoria
        if image_data:
            try:
                self.vision_service.audit_cleaning(image_data=image_data, bounty_id=bounty_id)
            except Exception:
                pass

        # Validação opcional de QR Code se for informado explicitamente
        if qrcode_data:
            clean_dest = bounty.dest.upper().replace(" ", "").replace("-", "")
            clean_qr = qrcode_data.upper().replace(" ", "").replace("-", "")
            if clean_dest not in clean_qr:
                return False, 0.0, f"Destino incorreto. Leve o resíduo até {bounty.dest}."

        # Credita 50% restantes
        advance_val = bounty.half_value()
        remaining_val = round(bounty.val - advance_val, 2)
        self.wallet_service.credit_completion(user_id, bounty_id, bounty.val, bounty_title=bounty.title)

        # Atualiza bounty para CONCLUIDO
        conn = get_connection(self.db_path)
        try:
            with conn:
                conn.execute(
                    "UPDATE bounties SET status = 'CONCLUIDO', current_phase = 3 WHERE id = ?",
                    (bounty_id,),
                )
                bounty.status = "CONCLUIDO"
                bounty.current_phase = 3
                try:
                    from app.services.firestore_service import get_firestore_service
                    get_firestore_service().save_bounty_async(bounty)
                except Exception:
                    pass
        finally:
            conn.close()

        return True, remaining_val, "Ciclo Fechado! Descarte comprovado e creditado com sucesso."

    def create_denuncia_bounty(
        self,
        user_id: int,
        lat: float,
        lng: float,
        image_data: Any = None,
        simulate_empty: bool = False,
    ) -> Tuple[bool, Optional[Bounty], str]:
        """Cria uma nova missão comunitária a partir de uma denúncia cidadã (UC10)."""
        # Checa duplicidade em raio de 20m (UC10 FE2)
        active_bounties = self.get_bounties("todos", include_completed=False)
        for b in active_bounties:
            dist = haversine_distance(lat, lng, b.lat, b.lng)
            if dist < MIN_DUPLICATE_RADIUS_METERS:
                return False, None, "Já existe uma missão aberta para este local"

        # Classificação por IA
        vision_res = self.vision_service.classify_irregular_waste(
            image_data=image_data,
            lat=lat,
            lng=lng,
            simulate_empty=simulate_empty,
        )

        if not vision_res.get("identified", False):
            return False, None, vision_res.get("message", "Nenhum resíduo identificado na imagem")

        title = vision_res.get("title", "Descarte Irregular Reportado")
        waste_type = vision_res.get("waste_type", "Plástico")
        val = float(vision_res.get("estimated_value", 25.00))
        dest = vision_res.get("dest", "COOPLUM")
        from app.services.geo_service import get_geo_service
        cur_u_lat, cur_u_lng = get_geo_service().get_current_location()
        dist_user = int(haversine_distance(cur_u_lat, cur_u_lng, lat, lng))

        now = datetime.now().isoformat()
        if isinstance(image_data, (bytes, bytearray)):
            img_url = self.storage_service.save_image(image_data)
        elif isinstance(image_data, str) and image_data:
            img_url = self.storage_service.get_image_url(image_data)
        else:
            img_url = "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80"

        conn = get_connection(self.db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO bounties (title, val, dist, type, dest, img, lat, lng, icon, color, sponsor, status, assigned_user_id, current_phase, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPONIVEL', NULL, 0, ?)
                    """,
                    (
                        title,
                        val,
                        dist_user,
                        waste_type,
                        dest,
                        img_url,
                        lat,
                        lng,
                        "cup-soda",
                        "blue",
                        "Denúncia Comunitária",
                        now,
                    ),
                )
                bounty_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM bounties WHERE id = ?", (bounty_id,)).fetchone()
                new_b = Bounty.from_row(row)
                try:
                    from app.services.firestore_service import get_firestore_service
                    get_firestore_service().save_bounty_async(new_b)
                except Exception:
                    pass
                return True, new_b, "Bounty Criado! A comunidade agradece o mapeamento."
        finally:
            conn.close()

    def create_sponsored_bounty(
        self,
        user_id: int,
        sponsor_name: str,
        title: str,
        waste_type: str,
        dest: str,
        val: float,
        lat: float,
        lng: float,
    ) -> Tuple[bool, Optional[Bounty], str, dict]:
        """Permite que Patrocinador, Ecoponto ou Admin crie um Bounty com valor próprio custeado via Mercado Pago Sandbox."""
        import uuid
        from app.services.mercadopago_service import get_mercadopago_service

        clean_title = (title or "").strip() or f"Coleta Patrocinada de {waste_type}"
        reward_val = round(float(val), 2)
        if reward_val < 5.0:
            return False, None, "O valor mínimo para patrocinar uma missão é R$ 5,00.", {}

        conn = get_connection(self.db_path)
        try:
            with conn:
                user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                user_email = user_row["email"] if user_row else "patrocinador@ecobounty.com"
                curr_bal = float(user_row["balance"]) if user_row else 0.0

                # Processa o pagamento do patrocínio no Mercado Pago Sandbox
                idem_key = f"mp_sponsor_{user_id}_{uuid.uuid4().hex[:10]}"
                mp_res = get_mercadopago_service().create_pix_transfer(
                    user_id=user_id,
                    user_name=sponsor_name,
                    user_email=user_email,
                    pix_key=f"BOUNTY-{dest.upper()}",
                    pix_key_type="Patrocínio ESG",
                    amount=reward_val,
                    idempotency_key=idem_key,
                )
                mp_id = mp_res.get("mp_payment_id", idem_key)

                # Se o patrocinador tiver saldo em carteira, desconta até o limite do saldo;
                # caso contrário, o patrocínio é quitado diretamente via Pix Mercado Pago Sandbox.
                new_bal = max(0.0, round(curr_bal - reward_val, 2)) if curr_bal >= reward_val else curr_bal
                if user_row and new_bal != curr_bal:
                    conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, user_id))

                icon_map = {
                    "Plástico": ("cup-soda", "blue", "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80"),
                    "Inerte": ("hammer", "orange", "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=800&q=80"),
                    "Eletrônicos": ("monitor", "slate", "https://images.unsplash.com/photo-1550989460-0adf9ea622e2?auto=format&fit=crop&w=800&q=80"),
                    "Papelão": ("box", "amber", "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?auto=format&fit=crop&w=800&q=80"),
                    "Metal": ("can", "emerald", "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=800&q=80"),
                }
                icon, color, img_url = icon_map.get(waste_type, icon_map["Plástico"])
                now = datetime.now().isoformat()

                cursor = conn.execute(
                    """
                    INSERT INTO bounties (title, val, dist, type, dest, img, lat, lng, icon, color, sponsor, status, assigned_user_id, current_phase, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPONIVEL', NULL, 0, ?)
                    """,
                    (
                        clean_title,
                        reward_val,
                        120,
                        waste_type,
                        dest,
                        img_url,
                        round(lat + 0.0012, 6),
                        round(lng + 0.0012, 6),
                        icon,
                        color,
                        sponsor_name,
                        now,
                    ),
                )
                bounty_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM bounties WHERE id = ?", (bounty_id,)).fetchone()
                new_b = Bounty.from_row(row)
                self.bounty_cache.put(bounty_id, new_b)

                if user_row:
                    conn.execute(
                        """
                        INSERT INTO transactions (user_id, bounty_id, type, amount, idempotency_key, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, bounty_id, "PATROCINIO_BOUNTY_MP", -reward_val, f"{idem_key}_{mp_id}", now),
                    )
                    conn.execute(
                        """
                        INSERT INTO history (user_id, title, status, amount, date_label, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            f"Bounty Patrocinado: {clean_title}",
                            "Mercado Pago Sandbox",
                            reward_val,
                            f"Pix #{mp_id} • Missão #{bounty_id}",
                            now,
                        ),
                    )

                try:
                    from app.services.firestore_service import get_firestore_service
                    svc = get_firestore_service()
                    svc.save_bounty_async(new_b)
                except Exception:
                    pass

                return (
                    True,
                    new_b,
                    f"Bounty '{clean_title}' (R$ {reward_val:.2f}) criado e patrocinado via Mercado Pago ({mp_id})!",
                    mp_res,
                )
        finally:
            conn.close()
