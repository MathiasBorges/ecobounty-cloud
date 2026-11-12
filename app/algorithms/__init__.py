"""Módulo de Algoritmos Avançados do EcoBounty.

Contempla:
- Diferencial 2: Algoritmos de Grafos (Dijkstra, BFS, Malha de Maceió) + Visualizador Matplotlib
- Diferencial 3: Algoritmos de Ordenação (Bubble, Insertion, Selection, QuickSort) + Benchmark Matplotlib
"""
from app.algorithms.sorting import (
    bubble_sort,
    insertion_sort,
    selection_sort,
    quick_sort,
    sort_bounties_by_reward,
    sort_bounties_by_distance,
    sort_bounties_by_urgency,
    benchmark_sorting_algorithms,
    SortMetrics,
)
from app.algorithms.graphs import (
    GeoNode,
    GeoEdge,
    MaceioEcoGraph,
    build_maceio_recycling_graph,
)
try:
    from app.algorithms.visualizer import plot_sorting_benchmark, plot_geo_graph
except (ImportError, ModuleNotFoundError):
    plot_sorting_benchmark = None
    plot_geo_graph = None

__all__ = [
    "bubble_sort",
    "insertion_sort",
    "selection_sort",
    "quick_sort",
    "sort_bounties_by_reward",
    "sort_bounties_by_distance",
    "sort_bounties_by_urgency",
    "benchmark_sorting_algorithms",
    "SortMetrics",
    "GeoNode",
    "GeoEdge",
    "MaceioEcoGraph",
    "build_maceio_recycling_graph",
    "plot_sorting_benchmark",
    "plot_geo_graph",
]
