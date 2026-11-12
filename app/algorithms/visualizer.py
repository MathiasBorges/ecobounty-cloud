"""Diferenciais 2 e 3 (2ª Unidade - Obrigatório): Visualização Gráfica com Matplotlib.

Gera gráficos comparativos de alto nível para a apresentação da disciplina:
1. Gráfico comparativo de desempenho dos algoritmos de ordenação (Tempo em ms vs N).
2. Gráfico do Grafo de Geolocalização de Maceió com a Rota Ótima (Dijkstra) destacada.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Backend headless seguro para execução em servidor e testes
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from app.algorithms.graphs import MaceioEcoGraph, build_maceio_recycling_graph
from app.algorithms.sorting import benchmark_sorting_algorithms


def plot_sorting_benchmark(
    benchmark_data: Optional[Dict[str, Dict[str, List[float]]]] = None,
    sizes: Optional[List[int]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Gera gráfico comparativo de desempenho (Tempo em ms x Tamanho N) entre os métodos de ordenação.

    Salva em disco e retorna o caminho do arquivo gerado.
    """
    if sizes is None:
        sizes = [50, 100, 250, 500, 1000]

    if benchmark_data is None:
        benchmark_data = benchmark_sorting_algorithms(sizes=sizes)

    if output_path is None:
        output_path = "Entregas/benchmark_ordenacao.png"

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=150)
    fig.patch.set_facecolor("#0f172a")

    for ax in (ax1, ax2):
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#cbd5e1")
        ax.xaxis.label.set_color("#f8fafc")
        ax.yaxis.label.set_color("#f8fafc")
        ax.title.set_color("#38bdf8")
        for spine in ax.spines.values():
            spine.set_color("#475569")
        ax.grid(True, linestyle="--", alpha=0.3, color="#64748b")

    # Cores distintas por algoritmo
    colors = {
        "Bubble Sort": "#ef4444",      # Vermelho
        "Insertion Sort": "#f59e0b",   # Âmbar
        "Selection Sort": "#3b82f6",   # Azul
        "QuickSort": "#10b981",        # Verde Esmeralda (Melhor Desempenho)
    }

    markers = {
        "Bubble Sort": "o",
        "Insertion Sort": "s",
        "Selection Sort": "^",
        "QuickSort": "D",
    }

    # Gráfico 1: Tempo de Execução (ms) x N
    for algo, metric in benchmark_data.items():
        times = metric["time_ms"]
        ax1.plot(
            sizes,
            times,
            marker=markers.get(algo, "o"),
            color=colors.get(algo, "#ffffff"),
            linewidth=2.5,
            markersize=7,
            label=algo,
        )

    ax1.set_title("Comparativo de Tempo de Execução (ms) vs Tamanho (N)", fontsize=13, fontweight="bold", pad=12)
    ax1.set_xlabel("Número de Elementos (N)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Tempo Médio de Execução (ms)", fontsize=11, fontweight="bold")
    leg1 = ax1.legend(facecolor="#334155", edgecolor="#64748b", labelcolor="#f8fafc", loc="upper left")
    leg1.get_frame().set_alpha(0.85)

    # Gráfico 2: Número de Comparações x N (Escala Logarítmica)
    for algo, metric in benchmark_data.items():
        comps = metric["comparisons"]
        ax2.plot(
            sizes,
            comps,
            marker=markers.get(algo, "o"),
            color=colors.get(algo, "#ffffff"),
            linewidth=2.5,
            markersize=7,
            label=algo,
        )

    ax2.set_title("Comparativo de Complexidade (Comparações vs N)", fontsize=13, fontweight="bold", pad=12)
    ax2.set_xlabel("Número de Elementos (N)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Quantidade de Comparações (Log)", fontsize=11, fontweight="bold")
    ax2.set_yscale("log")
    leg2 = ax2.legend(facecolor="#334155", edgecolor="#64748b", labelcolor="#f8fafc", loc="upper left")
    leg2.get_frame().set_alpha(0.85)

    plt.suptitle("EcoBounty - Diferencial 3: Benchmark Comparativo de Algoritmos de Ordenação", fontsize=15, fontweight="bold", color="#f8fafc", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(str(out_file), dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return str(out_file)


def plot_geo_graph(
    graph: Optional[MaceioEcoGraph] = None,
    highlight_path: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Gera visualização gráfica do Grafo de Maceió com coordenadas geográficas e Dijkstra destacado.

    Salva em disco e retorna o caminho do arquivo gerado.
    """
    if graph is None:
        graph = build_maceio_recycling_graph()

    if highlight_path is None:
        # Padrão: menor caminho do Trapiche da Barra até a cooperativa COOPLUM em Jacarecica
        highlight_path, total_km = graph.dijkstra_shortest_path("ECO_TRAPICHE", "COOPLUM")
    else:
        total_km = 0.0
        if len(highlight_path) > 1:
            for i in range(len(highlight_path) - 1):
                u, v = highlight_path[i], highlight_path[i + 1]
                for neighbor, weight in graph.adj_list.get(u, []):
                    if neighbor == v:
                        total_km += weight
                        break
        total_km = round(total_km, 2)

    if output_path is None:
        output_path = "Entregas/grafo_maceio_rotas.png"

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(13, 9), dpi=150)
    fig.patch.set_facecolor("#0b1329")
    ax.set_facecolor("#111c38")

    ax.tick_params(colors="#94a3b8")
    ax.xaxis.label.set_color("#e2e8f0")
    ax.yaxis.label.set_color("#e2e8f0")
    ax.title.set_color("#38bdf8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.grid(True, linestyle=":", alpha=0.35, color="#475569")

    # Conjunto de arestas da rota destacada
    path_edges = set()
    if highlight_path and len(highlight_path) > 1:
        for i in range(len(highlight_path) - 1):
            u, v = highlight_path[i], highlight_path[i + 1]
            path_edges.add((u, v))
            path_edges.add((v, u))

    # Desenha as arestas
    drawn_edges = set()
    for u, neighbors in graph.adj_list.items():
        node_u = graph.get_node(u)
        if not node_u:
            continue
        for v, weight in neighbors:
            edge_key = tuple(sorted([u, v]))
            if edge_key in drawn_edges:
                continue
            drawn_edges.add(edge_key)

            node_v = graph.get_node(v)
            if not node_v:
                continue

            is_highlighted = (u, v) in path_edges or (v, u) in path_edges
            edge_color = "#10b981" if is_highlighted else "#475569"
            edge_width = 3.5 if is_highlighted else 1.2
            alpha = 1.0 if is_highlighted else 0.4
            zorder = 3 if is_highlighted else 1

            ax.plot(
                [node_u.lng, node_v.lng],
                [node_u.lat, node_v.lat],
                color=edge_color,
                linewidth=edge_width,
                alpha=alpha,
                zorder=zorder,
            )

            # Rótulo de peso (distância em km) no ponto médio da aresta
            mid_lng = (node_u.lng + node_v.lng) / 2.0
            mid_lat = (node_u.lat + node_v.lat) / 2.0
            if is_highlighted:
                ax.text(
                    mid_lng,
                    mid_lat,
                    f"{weight}km",
                    color="#6ee7b7",
                    fontsize=8,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#064e3b", edgecolor="#10b981", alpha=0.9),
                    zorder=4,
                )

    # Desenha os nós
    for node_id, node in graph.nodes.items():
        is_in_path = highlight_path is not None and node_id in highlight_path
        is_start = highlight_path is not None and len(highlight_path) > 0 and node_id == highlight_path[0]
        is_end = highlight_path is not None and len(highlight_path) > 0 and node_id == highlight_path[-1]

        if is_start:
            node_color = "#38bdf8"  # Azul Ciano brilhante (Origem)
            node_size = 220
        elif is_end:
            node_color = "#22c55e"  # Verde brilhante (Destino Cooperativa)
            node_size = 240
        elif node.node_type == "cooperativa":
            node_color = "#10b981"  # Verde
            node_size = 200
        elif is_in_path:
            node_color = "#34d399"  # Rota intermediária
            node_size = 170
        else:
            node_color = "#64748b"  # Cinza neutro
            node_size = 120

        ax.scatter(
            node.lng,
            node.lat,
            s=node_size,
            color=node_color,
            edgecolors="#ffffff",
            linewidth=1.8,
            zorder=5,
        )

        # Rótulo do nó com offset adaptativo
        label_text = node.name.replace("Ecoponto ", "").replace("Cooperativa ", "")
        ax.annotate(
            label_text,
            xy=(node.lng, node.lat),
            xytext=(0, 10),
            textcoords="offset points",
            color="#f1f5f9" if is_in_path else "#94a3b8",
            fontsize=8.5,
            fontweight="bold" if is_in_path else "normal",
            ha="center",
            bbox=dict(
                boxstyle="round,pad=0.2",
                facecolor="#0f172a" if is_in_path else "#1e293b",
                edgecolor=node_color,
                alpha=0.85,
            ),
            zorder=6,
        )

    # Legenda explicativa
    legend_elements = [
        mpatches.Patch(color="#38bdf8", label="Ponto de Partida da Coleta"),
        mpatches.Patch(color="#22c55e", label="Destino Final: Cooperativa COOPLUM"),
        mpatches.Patch(color="#10b981", label=f"Rota Ótima (Dijkstra) [{len(highlight_path)} nós • {total_km}km]"),
        mpatches.Patch(color="#64748b", label="Rede de Ecopontos Conectada"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", facecolor="#1e293b", edgecolor="#475569", labelcolor="#f8fafc", fontsize=9)

    ax.set_title("EcoBounty - Diferencial 2: Malha de Ecopontos e Roteamento Dijkstra em Maceió - AL", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Longitude Geográfica (Graus)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Latitude Geográfica (Graus)", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(str(out_file), dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return str(out_file)
