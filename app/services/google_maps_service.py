"""Serviço de Integração Oficial da Google Maps Platform.

Implementa:
1. Geocoding / Reverse Geocoding (endereço real, bairro, rua e número via GPS).
2. Routes / Directions API (rotas a pé reais, distância viária pelas calçadas e ETA).
3. Maps Static API (geração dinâmica de mapas sem limites geográficos, mundial).
4. Deep-linking de navegação assistida por voz no app Google Maps oficial.
"""
import base64
import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from app.config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

_GMAPS_STATIC_CACHE: Dict[str, str] = {}
_REVERSE_GEO_CACHE: Dict[Tuple[float, float], Dict[str, str]] = {}
_ROUTE_CACHE: Dict[Tuple[float, float, float, float], Dict[str, Any]] = {}
_GOOGLE_API_DENIED: bool = False


def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """Decodifica uma polyline codificada do Google Maps em uma lista de tuplas (lat, lng)."""
    points = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        points.append((lat / 1e5, lng / 1e5))

    return points


class GoogleMapsService:
    _instance: Optional["GoogleMapsService"] = None

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GOOGLE_MAPS_API_KEY

    @classmethod
    def get_instance(cls) -> "GoogleMapsService":
        if cls._instance is None:
            cls._instance = GoogleMapsService()
        return cls._instance

    def is_available(self) -> bool:
        """Indica se a chave da API está configurada com formato oficial Google Cloud / Maps (prefixo AIza)."""
        return bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key.startswith("AIza")
            and self.api_key != "YOUR_GOOGLE_MAPS_API_KEY"
        )

    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """Converte coordenadas GPS em tempo real em endereço legível via Google Maps Geocoding API."""
        global _GOOGLE_API_DENIED
        cache_key = (round(lat, 4), round(lng, 4))
        if cache_key in _REVERSE_GEO_CACHE:
            return _REVERSE_GEO_CACHE[cache_key]

        # 1. Consulta em tempo real via Google Maps Geocoding REST API
        if self.is_available() and len(self.api_key.strip()) > 20 and not _GOOGLE_API_DENIED:
            try:
                url = (
                    f"https://maps.googleapis.com/maps/api/geocode/json?"
                    f"latlng={lat:.6f},{lng:.6f}&language=pt-BR&key={self.api_key}"
                )
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "EcoBountyApp/1.0 (google-maps-platform)"},
                )
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("status") == "REQUEST_DENIED":
                        _GOOGLE_API_DENIED = True
                    elif data.get("status") == "OK" and data.get("results"):
                        first_res = data["results"][0]
                        formatted_address = first_res.get("formatted_address", "")
                        street = ""
                        neighborhood = ""
                        city = ""
                        state = ""

                        for comp in first_res.get("address_components", []):
                            types = comp.get("types", [])
                            if "route" in types:
                                street = comp.get("long_name", "")
                            elif "sublocality_level_1" in types or "sublocality" in types or "neighborhood" in types:
                                neighborhood = comp.get("long_name", "")
                            elif "administrative_area_level_2" in types:
                                city = comp.get("long_name", "")
                            elif "administrative_area_level_1" in types:
                                state = comp.get("short_name", "")

                        short_label = neighborhood or street or city or f"GPS ({lat:.4f}, {lng:.4f})"
                        full_label = f"{short_label}, {city} - {state}" if (city and state) else formatted_address
                        res = {
                            "formatted_address": formatted_address or f"Localização GPS ({lat:.5f}, {lng:.5f})",
                            "street": street,
                            "neighborhood": neighborhood or "Maceió",
                            "city": city or "Maceió",
                            "state": state or "AL",
                            "short_label": short_label,
                            "full_label": full_label,
                        }
                        _REVERSE_GEO_CACHE[cache_key] = res
                        return res
            except Exception as e:
                logger.debug(f"Falha no Reverse Geocoding Google: {e}")

        # 2. Consulta rápida via API gratuita BigDataCloud (sem necessidade de chaves, retorno instantâneo)
        try:
            free_url = (
                f"https://api.bigdatacloud.net/data/reverse-geocode-client?"
                f"latitude={lat:.6f}&longitude={lng:.6f}&localityLanguage=pt"
            )
            req = urllib.request.Request(
                free_url,
                headers={"User-Agent": "EcoBountyApp/1.0"},
            )
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                data = json.loads(resp.read().decode())
                city = data.get("city") or data.get("locality") or ""
                locality = data.get("locality") or ""
                subdiv = data.get("principalSubdivision") or "AL"
                state = "AL" if "alagoas" in subdiv.lower() else subdiv[:2].upper()

                if locality and city and locality.lower() != city.lower():
                    short_label = f"{locality}, {city}"
                    full_label = f"{locality}, {city} - {state}"
                elif city:
                    short_label = f"{city}, {state}"
                    full_label = f"{city}, {state}"
                else:
                    short_label = ""
                    full_label = ""

                if short_label:
                    res = {
                        "formatted_address": full_label,
                        "street": "",
                        "neighborhood": locality or city,
                        "city": city or "Maceió",
                        "state": state,
                        "short_label": short_label,
                        "full_label": short_label,
                    }
                    _REVERSE_GEO_CACHE[cache_key] = res
                    return res
        except Exception:
            pass

        # 3. Fallback determinístico por malha geográfica de Alagoas (instantâneo e offline)
        short_label = "Maceió, AL"
        if -9.63 <= lat <= -9.52 and -35.86 <= lng <= -35.78:
            short_label = "Satuba, AL"
        elif -9.54 <= lat <= -9.42 and -35.88 <= lng <= -35.77:
            short_label = "Rio Largo, AL"
        elif -9.78 <= lat <= -9.68 and -35.93 <= lng <= -35.82:
            short_label = "Marechal Deodoro, AL"
        elif -9.67 <= lat <= -9.64 and -35.72 <= lng <= -35.69:
            short_label = "Ponta Verde, Maceió"
        elif -9.68 <= lat <= -9.65 and -35.72 <= lng <= -35.70:
            short_label = "Pajuçara, Maceió"
        elif -9.66 <= lat <= -9.63 and -35.72 <= lng <= -35.69:
            short_label = "Jatiúca, Maceió"
        elif -9.68 <= lat <= -9.65 and -35.75 <= lng <= -35.72:
            short_label = "Centro, Maceió"
        elif -9.60 <= lat <= -9.53 and -35.78 <= lng <= -35.72:
            short_label = "Tabuleiro, Maceió"
        elif -9.58 <= lat <= -9.51 and -35.74 <= lng <= -35.68:
            short_label = "Benedito Bentes, Maceió"

        res = {
            "formatted_address": short_label,
            "street": "",
            "neighborhood": short_label.split(",")[0].strip(),
            "city": short_label.split(",")[-1].strip(),
            "state": "AL",
            "short_label": short_label,
            "full_label": short_label,
        }
        _REVERSE_GEO_CACHE[cache_key] = res
        return res

    def compute_walking_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> Optional[Dict[str, Any]]:
        """Calcula rota a pé real e precisa pelas calçadas via Cache + Routes API + Fallback Viário Imediato."""
        global _GOOGLE_API_DENIED
        cache_key = (
            round(origin_lat, 4),
            round(origin_lng, 4),
            round(dest_lat, 4),
            round(dest_lng, 4),
        )
        if cache_key in _ROUTE_CACHE:
            return _ROUTE_CACHE[cache_key]

        # 1. Tenta via Google Routes API v2 se a chave for válida e não tiver sido negada
        if self.is_available() and len(self.api_key.strip()) > 20 and not _GOOGLE_API_DENIED:
            try:
                routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
                payload = json.dumps({
                    "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
                    "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
                    "travelMode": "WALK",
                    "languageCode": "pt-BR",
                }).encode("utf-8")

                req = urllib.request.Request(
                    routes_url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
                        "User-Agent": "EcoBountyApp/1.0 (google-maps-platform)",
                    },
                )
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("routes"):
                        route = data["routes"][0]
                        dist_m = int(route.get("distanceMeters", 0))
                        dur_str = route.get("duration", "0s").replace("s", "")
                        dur_s = int(dur_str) if dur_str.isdigit() else 0
                        dist_text = f"{dist_m} m" if dist_m < 1000 else f"{dist_m/1000:.1f} km"
                        dur_text = f"{max(1, round(dur_s / 60))} min"
                        encoded = route.get("polyline", {}).get("encodedPolyline", "")
                        coords = decode_polyline(encoded) if encoded else []

                        res = {
                            "distance_meters": dist_m,
                            "distance_text": dist_text,
                            "duration_seconds": dur_s,
                            "duration_text": dur_text,
                            "start_address": "",
                            "end_address": "",
                            "polyline_points": coords,
                        }
                        _ROUTE_CACHE[cache_key] = res
                        return res
            except urllib.error.HTTPError as e:
                if e.code in (400, 403):
                    _GOOGLE_API_DENIED = True
                logger.debug(f"Routes API v2 falhou ({e.code})")
            except Exception as e:
                logger.debug(f"Routes API v2 falhou: {e}")

        # 2. Consulta em tempo real via OSRM Foot (Open Source Routing Machine) - 100% Gratuito, Zero Custo, Sem Cartão
        try:
            osrm_url = (
                f"https://router.project-osrm.org/route/v1/foot/"
                f"{origin_lng:.6f},{origin_lat:.6f};{dest_lng:.6f},{dest_lat:.6f}"
                f"?overview=full&geometries=geojson&steps=true"
            )
            req = urllib.request.Request(
                osrm_url,
                headers={"User-Agent": "EcoBountyApp/1.0 (mathiasbm377@gmail.com)"},
            )
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                data = json.loads(resp.read().decode())
                if data.get("routes"):
                    route = data["routes"][0]
                    dist_m = int(route.get("distance", 0))
                    dur_s = int(route.get("duration", 0))
                    dist_text = f"{dist_m} m" if dist_m < 1000 else f"{dist_m/1000:.1f} km"
                    dur_text = f"{max(1, round(dur_s / 60))} min"
                    # Converte GeoJSON [lng, lat] para tuplas (lat, lng)
                    coords = [
                        (float(pt[1]), float(pt[0]))
                        for pt in route.get("geometry", {}).get("coordinates", [])
                    ]
                    res = {
                        "distance_meters": dist_m,
                        "distance_text": dist_text,
                        "duration_seconds": dur_s,
                        "duration_text": dur_text,
                        "start_address": "",
                        "end_address": "",
                        "polyline_points": coords if len(coords) >= 2 else [(origin_lat, origin_lng), (dest_lat, dest_lng)],
                        "provider": "OSRM Foot",
                    }
                    _ROUTE_CACHE[cache_key] = res
                    return res
        except Exception as e:
            logger.debug(f"OSRM Foot Routing falhou ou offline: {e}")

        # 3. Fallback Instantâneo Geodésico Local (0ms - zero bloqueio)
        import math
        r_earth = 6371000.0  # metros
        phi1 = math.radians(origin_lat)
        phi2 = math.radians(dest_lat)
        delta_phi = math.radians(dest_lat - origin_lat)
        delta_lambda = math.radians(dest_lng - origin_lng)
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        dist_m = round(r_earth * c)
        dur_s = round(dist_m / 1.33)  # Caminhada a ~4.8 km/h = 1.33 m/s
        dist_text = f"{dist_m} m" if dist_m < 1000 else f"{dist_m/1000:.1f} km"
        dur_text = f"{max(1, round(dur_s / 60))} min"

        res = {
            "distance_meters": dist_m,
            "distance_text": dist_text,
            "duration_seconds": dur_s,
            "duration_text": dur_text,
            "start_address": "",
            "end_address": "",
            "polyline_points": [(origin_lat, origin_lng), (dest_lat, dest_lng)],
        }
        _ROUTE_CACHE[cache_key] = res
        return res

    def get_static_map_url(
        self,
        center_lat: float,
        center_lng: float,
        zoom: int = 15,
        width: int = 600,
        height: int = 400,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        bounties: Optional[List[Any]] = None,
        map_type: str = "roadmap",
    ) -> str:
        """Gera URL oficial da Maps Static API com marcadores vetorizados em alta resolução."""
        base_url = "https://maps.googleapis.com/maps/api/staticmap?"
        params = [
            f"center={center_lat:.6f},{center_lng:.6f}",
            f"zoom={zoom}",
            f"size={width}x{height}",
            "scale=2",
            f"maptype={map_type}",
        ]

        # Marcador do Usuário (Pino azul)
        if user_lat is not None and user_lng is not None:
            params.append(f"markers=color:blue%7Clabel:U%7C{user_lat:.6f},{user_lng:.6f}")

        # Marcadores dos Bounties (Pinos verdes com símbolo de valor)
        if bounties:
            for b in bounties[:8]:
                b_lat = getattr(b, "lat", None)
                b_lng = getattr(b, "lng", None)
                if b_lat is not None and b_lng is not None:
                    params.append(f"markers=color:green%7Clabel:$%7C{b_lat:.6f},{b_lng:.6f}")

        if self.is_available():
            params.append(f"key={self.api_key}")

        return base_url + "&".join(params)

    def fetch_static_map_base64(
        self,
        center_lat: float,
        center_lng: float,
        zoom: int = 15,
        width: int = 400,
        height: int = 400,
        map_type: str = "roadmap",
    ) -> Optional[str]:
        """Baixa a imagem oficial do Google Maps Static API e retorna em base64 com cache de alta performance."""
        global _GOOGLE_API_DENIED
        if not (self.is_available() and len(self.api_key.strip()) > 20 and not _GOOGLE_API_DENIED):
            return None

        # Arredonda ligeiramente para maximizar reaproveitamento de cache durante pan/zoom
        c_lat = round(center_lat, 4)
        c_lng = round(center_lng, 4)
        cache_key = f"{c_lat}_{c_lng}_{zoom}_{width}_{height}_{map_type}"
        if cache_key in _GMAPS_STATIC_CACHE:
            return _GMAPS_STATIC_CACHE[cache_key]

        try:
            url = self.get_static_map_url(
                center_lat=c_lat,
                center_lng=c_lng,
                zoom=zoom,
                width=width,
                height=height,
                map_type=map_type,
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "EcoBountyApp/1.0 (google-maps-platform)"},
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = resp.read()
                b64_str = base64.b64encode(data).decode("ascii")
                _GMAPS_STATIC_CACHE[cache_key] = b64_str
                return b64_str
        except urllib.error.HTTPError as e:
            if e.code in (400, 403):
                _GOOGLE_API_DENIED = True
            logger.debug(f"Falha ao obter mapa estático do Google Maps ({e.code}): {e}")
            return None
        except Exception as e:
            logger.debug(f"Falha ao obter mapa estático do Google Maps: {e}")
            return None

    def get_navigation_url(
        self,
        dest_lat: float,
        dest_lng: float,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
    ) -> str:
        """Gera URL direta de navegação a pé curva a curva por voz no Google Maps oficial."""
        if origin_lat is not None and origin_lng is not None:
            return (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={origin_lat:.6f},{origin_lng:.6f}"
                f"&destination={dest_lat:.6f},{dest_lng:.6f}"
                f"&travelmode=walking"
            )
        return f"https://www.google.com/maps/dir/?api=1&destination={dest_lat:.6f},{dest_lng:.6f}&travelmode=walking"


def get_google_maps_service() -> GoogleMapsService:
    return GoogleMapsService.get_instance()


def is_google_api_denied() -> bool:
    """Retorna True se as chamadas de API do Google foram rejeitadas (ex: chave inválida ou 403)."""
    global _GOOGLE_API_DENIED
    return _GOOGLE_API_DENIED


