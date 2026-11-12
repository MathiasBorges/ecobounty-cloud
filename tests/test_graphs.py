"""Testes unitários rigorosos para o Diferencial 2 (Algoritmos de Grafos e Geolocalização).

Cobre:
- Construção da Malha de Ecopontos e Cooperativas de Maceió - AL
- Algoritmo de Dijkstra para cálculo de menor caminho
- Busca em Largura (BFS) para alcance e conectividade
- Localização geográfica do nó mais próximo (Haversine / Euclidiana)
- Geração visual do mapa de rotas com Matplotlib
"""
from pathlib import Path
import pytest

from app.algorithms.graphs import (
    GeoNode,
    MaceioEcoGraph,
    build_maceio_recycling_graph,
)
from app.algorithms.visualizer import plot_geo_graph


def test_maceio_graph_structure():
    g = build_maceio_recycling_graph()
    assert len(g.nodes) >= 10
    assert "COOPLUM" in g.nodes
    assert "ECO_JATIUCA" in g.nodes
    assert "ECO_PONTA_VERDE" in g.nodes

    # Verifica se os nós têm coordenadas válidas de Maceió (-9.x, -35.x)
    for node in g.nodes.values():
        assert -10.0 <= node.lat <= -9.0
        assert -36.0 <= node.lng <= -35.0


def test_dijkstra_shortest_path():
    g = build_maceio_recycling_graph()

    # Menor caminho de Pajuçara até COOPLUM (Jacarecica)
    path, dist_km = g.dijkstra_shortest_path("ECO_PAJUCARA", "COOPLUM")
    assert len(path) >= 3
    assert path[0] == "ECO_PAJUCARA"
    assert path[-1] == "COOPLUM"
    assert dist_km > 0.0

    # Rota a partir do Trapiche da Barra
    trapiche_path, trapiche_km = g.dijkstra_shortest_path("ECO_TRAPICHE", "COOPLUM")
    assert trapiche_path[0] == "ECO_TRAPICHE"
    assert trapiche_path[-1] == "COOPLUM"
    assert trapiche_km > dist_km  # Trapiche é mais distante que Pajuçara

    # Nós inexistentes
    invalid_path, inf_dist = g.dijkstra_shortest_path("NODE_INEXISTENTE", "COOPLUM")
    assert invalid_path == []
    assert inf_dist == float("inf")


def test_find_nearest_node_and_bfs():
    g = build_maceio_recycling_graph()

    # Coordenadas próximas à praia de Ponta Verde (-9.6610, -35.7020)
    nearest = g.find_nearest_node(-9.6612, -35.7025)
    assert nearest is not None
    assert nearest.node_id == "ECO_PONTA_VERDE"

    # Filtrando apenas por cooperativa
    coop = g.find_nearest_node(-9.65, -35.71, node_type="cooperativa")
    assert coop is not None
    assert coop.node_id == "COOPLUM"

    # BFS a partir do Centro Histórico deve alcançar toda a rede conectada
    reachable = g.bfs_reachable("ECO_CENTRO")
    assert len(reachable) == len(g.nodes)
    assert "COOPLUM" in reachable


def test_plot_geo_graph_generation(tmp_path):
    g = build_maceio_recycling_graph()
    out_file = tmp_path / "test_geo_graph.png"
    result_path = plot_geo_graph(g, output_path=str(out_file))

    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 5000

    # Teste de rota personalizada
    custom_path = ["ECO_TRAPICHE", "ECO_CENTRO", "ECO_FAROL"]
    custom_file = tmp_path / "test_custom_route.png"
    custom_res = plot_geo_graph(g, highlight_path=custom_path, output_path=str(custom_file))
    assert Path(custom_res).exists()


def test_dfs_explore():
    g = build_maceio_recycling_graph()
    dfs_nodes = g.dfs_explore("ECO_CENTRO")
    assert len(dfs_nodes) == len(g.nodes)
    assert "COOPLUM" in dfs_nodes
    assert dfs_nodes[0] == "ECO_CENTRO"

    # Vértice inexistente
    assert g.dfs_explore("NAO_EXISTE") == []

