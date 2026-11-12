"""Serviço de Registro e Localização de Ecopontos e Cooperativas Homologadas.

Fornece a malha georreferenciada exata de cooperativas de catadores (COOPLUM, COOPREL, COOPVILA)
e Ecopontos públicos da ALURB em Maceió e região metropolitana (Satuba, Rio Largo).
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Ecoponto:
    id: str
    name: str
    operator: str
    address: str
    neighborhood: str
    city: str
    lat: float
    lng: float
    accepted_materials: List[str]
    opening_hours: str
    qrcode_token: str
    phone: str = "(82) 3312-5300"
    is_active: bool = True

    def formatted_location(self) -> str:
        return f"{self.neighborhood}, {self.city} - AL"


# Base de dados oficial de Ecopontos e Cooperativas com coordenadas geográficas exatas
OFFICIAL_ECOPONTOS: List[Ecoponto] = [
    Ecoponto(
        id="satuba",
        name="Ecoponto Central Satuba",
        operator="Cooperativa Metropolitana de Reciclagem",
        address="Rodovia BR-104, Km 88, s/n (Próximo à Estação Ferroviária)",
        neighborhood="Centro",
        city="Satuba",
        lat=-9.5615,
        lng=-35.8230,
        accepted_materials=["Plástico", "Papelão", "Metais", "Vidro", "Eletrônicos"],
        opening_hours="Segunda a Sábado, das 07:00 às 17:00",
        qrcode_token="ECOPONTO-SATUBA-001",
        phone="(82) 3266-1212",
    ),
    Ecoponto(
        id="cooplum",
        name="COOPLUM - Coop. Recicladores Lixo Urbano Maceió",
        operator="Cooperativa dos Recicladores de Lixo Urbano de Maceió",
        address="Rua Dr. Arnaldo de Miranda, s/n - Jacarecica / Cruz das Almas",
        neighborhood="Jacarecica",
        city="Maceió",
        lat=-9.6205,
        lng=-35.7032,
        accepted_materials=["Plástico", "Garrafas PET", "Papelão", "Metais", "Embalagens"],
        opening_hours="Segunda a Sábado, das 07:00 às 17:00",
        qrcode_token="ECOPONTO-COOPLUM-001",
        phone="(82) 98845-1234",
    ),
    Ecoponto(
        id="cooprel",
        name="COOPREL - Cooperativa Regional de Alagoas",
        operator="Cooperativa Regional de Catadores de Alagoas",
        address="Av. Cachoeira do Meirim, 114 - Benedito Bentes",
        neighborhood="Benedito Bentes",
        city="Maceió",
        lat=-9.5542,
        lng=-35.7368,
        accepted_materials=["Plástico", "Eletrônicos", "Metais", "Papel"],
        opening_hours="Segunda a Sexta, das 08:00 às 17:00",
        qrcode_token="ECOPONTO-COOPREL-001",
        phone="(82) 99123-5678",
    ),
    Ecoponto(
        id="coopvila",
        name="COOPVILA - Coop. Vila Emater",
        operator="Cooperativa dos Catadores da Vila Emater",
        address="Alameda Santo Antônio, s/n - Cruz das Almas",
        neighborhood="Cruz das Almas",
        city="Maceió",
        lat=-9.6150,
        lng=-35.7100,
        accepted_materials=["Vidro", "Plástico", "Metais"],
        opening_hours="Segunda a Sexta, das 08:00 às 16:30",
        qrcode_token="ECOPONTO-COOPVILA-001",
        phone="(82) 99654-7890",
    ),
    Ecoponto(
        id="pajucara",
        name="Ecoponto Pajuçara (ALURB)",
        operator="ALURB - Prefeitura de Maceió",
        address="Av. Dr. Antônio Gouveia, s/n (Próximo à Praça Multieventos)",
        neighborhood="Pajuçara",
        city="Maceió",
        lat=-9.6698,
        lng=-35.7135,
        accepted_materials=["Recicláveis em Geral", "Podas de Árvore", "Entulho Pequeno Volume", "Móveis Desmontados"],
        opening_hours="Todos os dias, das 06:00 às 18:00",
        qrcode_token="ECOPONTO-PAJUCARA-001",
        phone="(82) 3312-5300",
    ),
    Ecoponto(
        id="jatiuca",
        name="Ecoponto Jatiúca / Stella Maris (ALURB)",
        operator="ALURB - Prefeitura de Maceió",
        address="Av. Dr. Júlio Marques Luz, s/n",
        neighborhood="Jatiúca",
        city="Maceió",
        lat=-9.6512,
        lng=-35.7089,
        accepted_materials=["Plástico", "Vidro", "Metais", "Papelão", "Inertes"],
        opening_hours="Todos os dias, das 06:00 às 18:00",
        qrcode_token="ECOPONTO-JATIUCA-001",
        phone="(82) 3312-5300",
    ),
    Ecoponto(
        id="tabuleiro",
        name="Ecoponto Tabuleiro dos Martins (ALURB)",
        operator="ALURB - Prefeitura de Maceió",
        address="Rua Doutor José Affonso de Mello / Av. Maceió",
        neighborhood="Tabuleiro do Martins",
        city="Maceió",
        lat=-9.5880,
        lng=-35.7650,
        accepted_materials=["Entulho da Construção", "Poda", "Volumosos", "Recicláveis"],
        opening_hours="Todos os dias, das 06:00 às 18:00",
        qrcode_token="ECOPONTO-TABULEIRO-001",
        phone="(82) 3312-5300",
    ),
    Ecoponto(
        id="santalucia",
        name="Ecoponto Santa Lúcia (ALURB)",
        operator="ALURB - Prefeitura de Maceió",
        address="Av. Belmiro Amorim, s/n",
        neighborhood="Santa Lúcia",
        city="Maceió",
        lat=-9.5785,
        lng=-35.7720,
        accepted_materials=["Entulho", "Móveis", "Recicláveis", "Papelão"],
        opening_hours="Todos os dias, das 06:00 às 18:00",
        qrcode_token="ECOPONTO-SANTALUCIA-001",
        phone="(82) 3312-5300",
    ),
    Ecoponto(
        id="dique",
        name="Ecoponto Dique Estrada (ALURB)",
        operator="ALURB - Prefeitura de Maceió",
        address="Av. Senador Rui Palmeira, s/n - Trapiche / Ponta Grossa",
        neighborhood="Trapiche da Barra",
        city="Maceió",
        lat=-9.6740,
        lng=-35.7550,
        accepted_materials=["Recicláveis", "Entulho", "Poda"],
        opening_hours="Todos os dias, das 06:00 às 18:00",
        qrcode_token="ECOPONTO-DIQUE-001",
        phone="(82) 3312-5300",
    ),
]


class EcopontoService:
    _instance: Optional["EcopontoService"] = None

    def __init__(self):
        self._ecopontos = list(OFFICIAL_ECOPONTOS)

    @classmethod
    def get_instance(cls) -> "EcopontoService":
        if cls._instance is None:
            cls._instance = EcopontoService()
        return cls._instance

    def list_all(self) -> List[Ecoponto]:
        """Retorna todos os ecopontos e cooperativas ativos."""
        return [e for e in self._ecopontos if e.is_active]

    def get_ecoponto(self, name_or_dest: Optional[str]) -> Ecoponto:
        """Localiza o Ecoponto pelo nome, sigla ou destino (ex: 'COOPLUM', 'Ecoponto ALURB', 'Satuba').

        Se não encontrado ou vazio, retorna o Ecoponto COOPLUM como referência padrão.
        """
        if not name_or_dest:
            return self._ecopontos[1]  # COOPLUM

        target = name_or_dest.strip().lower()

        # 1. Correspondência exata de ID ou sigla
        for eco in self._ecopontos:
            if eco.id.lower() == target:
                return eco
            if target in eco.name.lower() or target in eco.operator.lower():
                return eco

        # 2. Busca por bairro ou cidade
        for eco in self._ecopontos:
            if target in eco.neighborhood.lower() or target in eco.city.lower():
                return eco

        # Fallback padrão
        return self._ecopontos[1]

    def find_nearest(self, lat: float, lng: float, material: Optional[str] = None) -> Ecoponto:
        """Determina o Ecoponto ou Cooperativa mais próximo das coordenadas geográficas informadas."""
        def haversine(lat1, lon1, lat2, lon2):
            r = 6371000.0  # metros
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlam = math.radians(lon2 - lon1)
            a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
            return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        best_eco = self._ecopontos[0]
        min_dist = float("inf")

        for eco in self._ecopontos:
            if not eco.is_active:
                continue
            if material and not any(material.lower() in m.lower() for m in eco.accepted_materials):
                continue
            d = haversine(lat, lng, eco.lat, eco.lng)
            if d < min_dist:
                min_dist = d
                best_eco = eco

        return best_eco

    def get_by_qrcode(self, qrcode: str) -> Optional[Ecoponto]:
        """Localiza o Ecoponto pelo QR Code impresso no ponto de descarte."""
        token = qrcode.strip().upper()
        for eco in self._ecopontos:
            if eco.qrcode_token.upper() == token:
                return eco
        # Se for formato ECOPONTO-NOME-001, tenta casar
        for eco in self._ecopontos:
            if eco.id.upper() in token or eco.name.upper() in token:
                return eco
        return None


def get_ecoponto_service() -> EcopontoService:
    return EcopontoService.get_instance()
