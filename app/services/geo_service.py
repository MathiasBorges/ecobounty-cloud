"""Serviço de Geolocalização Real e Resolução de Posição (GeoService).

Detecta a localização geográfica real do usuário (via IP e GPS do navegador/dispositivo),
mantém estado reativo das coordenadas e calcula rotas viárias a partir do ponto físico real.
"""
import json
import logging
import os
import threading
import urllib.request
from typing import Dict, Optional, Tuple

from app.config import DEFAULT_USER_LAT, DEFAULT_USER_LNG

logger = logging.getLogger(__name__)


class GeoService:
    _instance: Optional["GeoService"] = None

    def __init__(self):
        self.user_lat: float = DEFAULT_USER_LAT
        self.user_lng: float = DEFAULT_USER_LNG
        self.city_label: str = "Maceió, AL"
        self.is_real_location: bool = False
        self.accuracy_meters: Optional[float] = None

        # Tenta detectar a localização física real em background (sem bloquear o startup da interface).
        # Na nuvem (ECOBOUNTY_CLOUD=1) o IP detectado seria o do datacenter, não o do usuário:
        # a posição vem exclusivamente do GPS do navegador de cada dispositivo.
        if os.getenv("ECOBOUNTY_CLOUD", "").lower() not in ("1", "true", "yes"):
            threading.Thread(target=self.detect_network_location, daemon=True).start()

    @classmethod
    def get_instance(cls) -> "GeoService":
        if cls._instance is None:
            cls._instance = GeoService()
        return cls._instance

    def detect_network_location(self) -> Tuple[float, float, str]:
        """Detecta a localização geográfica real do usuário via serviço de IP."""
        endpoints = [
            "https://get.geojs.io/v1/ip/geo.json",
            "https://freeipapi.com/api/json",
        ]
        for url in endpoints:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "EcoBountyApp/1.0 (mathiasbm377@gmail.com)"},
                )
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    data = json.loads(resp.read().decode())
                    lat = float(data.get("latitude"))
                    lng = float(data.get("longitude"))
                    city = data.get("city", "Maceió")
                    region = data.get("region", "AL")

                    # Se as coordenadas de rede/IP caírem no mar (enseada de Jaraguá / baía devido ao centroide do ISP),
                    # calibra para a zona urbana terrestre de Maceió (Centro/Farol)
                    if lat < -9.670 and lng > -35.742:
                        lat = -9.6635
                        lng = -35.7350

                    # Atualiza o estado interno
                    self.user_lat = lat
                    self.user_lng = lng
                    self.city_label = f"{city}, {region}"
                    self.is_real_location = True
                    self.accuracy_meters = 150.0  # Precisão estimada por rede
                    logger.info(f"Localização real detectada: {self.city_label} ({lat}, {lng})")
                    return self.user_lat, self.user_lng, self.city_label
            except Exception as e:
                logger.debug(f"Falha ao consultar {url}: {e}")

        # Fallback para o centro de Maceió
        self.user_lat = DEFAULT_USER_LAT
        self.user_lng = DEFAULT_USER_LNG
        self.city_label = "Maceió, AL"
        self.is_real_location = False
        return self.user_lat, self.user_lng, self.city_label

    def update_from_gps(
        self,
        lat: float,
        lng: float,
        accuracy: Optional[float] = None,
        label: Optional[str] = None,
    ) -> None:
        """Atualiza com dados de GPS de alta precisão e enriquece via Google Reverse Geocoding."""
        self.user_lat = float(lat)
        self.user_lng = float(lng)
        self.accuracy_meters = float(accuracy) if accuracy is not None else 15.0
        self.is_real_location = True

        if label:
            self.city_label = label
            return

        # Tenta enriquecer o rótulo do endereço com a Google Maps Platform (local ou cache)
        try:
            from app.services.google_maps_service import get_google_maps_service
            gmaps = get_google_maps_service()
            geo_info = gmaps.reverse_geocode(self.user_lat, self.user_lng)
            if geo_info and geo_info.get("full_label"):
                self.city_label = geo_info["full_label"]
        except Exception:
            pass

    def get_current_location(self) -> Tuple[float, float]:
        """Retorna as coordenadas atuais (lat, lng)."""
        return self.user_lat, self.user_lng

    def get_location_label(self) -> str:
        """Retorna o rótulo descritivo da localidade atual."""
        return self.city_label

    def get_location_info(self) -> Dict[str, any]:
        """Retorna o pacote completo com coordenadas e status de precisão."""
        return {
            "lat": self.user_lat,
            "lng": self.user_lng,
            "city_label": self.city_label,
            "is_real": self.is_real_location,
            "accuracy": self.accuracy_meters,
        }


def get_geo_service() -> GeoService:
    return GeoService.get_instance()
