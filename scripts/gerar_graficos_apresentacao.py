"""Script de Geração de Gráficos e Artefatos da Apresentação.

Executa os benchmarks dos 4 métodos de ordenação, constrói a malha de grafos
de Maceió com Dijkstra e salva os gráficos de alta resolução para
os slides e relatório técnico da disciplina.
"""
import sys
from pathlib import Path

# Adiciona raiz do projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.algorithms.visualizer import plot_sorting_benchmark, plot_geo_graph
from app.algorithms.graphs import build_maceio_recycling_graph
from app.algorithms.sorting import benchmark_sorting_algorithms
from app.cloud.cloud_architecture import save_cloud_artifacts


def main():
    print("=================================================================")
    print("ECOBOUNTY - GERADOR DE GRÁFICOS E ARTEFATOS EM NUVEM (UNIMA)")
    print("=================================================================")

    # 1. Benchmark dos Algoritmos de Ordenação (Diferencial 3)
    print("\n[1/3] Executando benchmark comparativo de ordenação...")
    sizes = [50, 100, 250, 500, 1000, 2000, 3000]
    print(f" -> Tamanhos de entrada avaliados: {sizes}")
    benchmark_data = benchmark_sorting_algorithms(sizes=sizes, repetitions=3)

    out_bench_entregas = "Entregas/benchmark_ordenacao.png"
    out_bench_assets = "app/assets/benchmark_ordenacao.png"
    plot_sorting_benchmark(benchmark_data, sizes=sizes, output_path=out_bench_entregas)
    plot_sorting_benchmark(benchmark_data, sizes=sizes, output_path=out_bench_assets)
    print(f" -> Gráficos de ordenação salvos em:")
    print(f"    - {out_bench_entregas}")
    print(f"    - {out_bench_assets}")

    # 2. Grafo de Maceió e Roteamento Dijkstra (Diferencial 2)
    print("\n[2/3] Gerando mapa visual do Grafo de Maceió e rota ótima Dijkstra...")
    g = build_maceio_recycling_graph()
    path, dist_km = g.dijkstra_shortest_path("ECO_TRAPICHE", "COOPLUM")
    print(f" -> Rota calculada via Dijkstra: {' -> '.join(path)}")
    print(f" -> Distância total percorrida: {dist_km} km")

    out_graph_entregas = "Entregas/grafo_maceio_rotas.png"
    out_graph_assets = "app/assets/grafo_maceio_rotas.png"
    plot_geo_graph(g, highlight_path=path, output_path=out_graph_entregas)
    plot_geo_graph(g, highlight_path=path, output_path=out_graph_assets)
    print(f" -> Mapas do grafo salvos em:")
    print(f"    - {out_graph_entregas}")
    print(f"    - {out_graph_assets}")

    # 3. Artefatos de Infraestrutura em Nuvem Google Cloud / Firebase
    print("\n[3/3] Exportando regras e configurações do Google Cloud & Firebase...")
    rules_p, json_p = save_cloud_artifacts()
    print(f" -> Firestore Security Rules: {rules_p}")
    print(f" -> Firebase Config JSON: {json_p}")

    print("\nTodos os artefatos foram gerados com sucesso!")


if __name__ == "__main__":
    main()
