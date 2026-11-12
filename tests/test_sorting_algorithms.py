"""Testes unitários rigorosos para o Diferencial 3 (Algoritmos de Ordenação).

Cobre:
- Bubble Sort, Insertion Sort, Selection Sort, QuickSort
- Casos limites: listas vazias, 1 elemento, já ordenadas, invertidas, duplicatas
- Ordenação com chave personalizada e ordem decrescente (reverse=True)
- Funções de domínio do EcoBounty (sort_bounties_by_reward, distance, urgency)
- Benchmark comparativo e geração de gráficos com Matplotlib
"""
import random
from pathlib import Path
import pytest

from app.algorithms.sorting import (
    bubble_sort,
    insertion_sort,
    selection_sort,
    quick_sort,
    sort_bounties_by_reward,
    sort_bounties_by_distance,
    sort_bounties_by_urgency,
    benchmark_sorting_algorithms,
)
from app.algorithms.visualizer import plot_sorting_benchmark
from app.models.bounty import Bounty


@pytest.fixture
def sample_bounties():
    return [
        Bounty(id=1, title="Lixo 1", val=25.0, dist=150, type="Plástico", dest="COOPLUM", img="", lat=-9.66, lng=-35.73, created_at="2026-05-01"),
        Bounty(id=2, title="Lixo 2", val=80.0, dist=50, type="Metal", dest="COOPLUM", img="", lat=-9.65, lng=-35.72, created_at="2026-05-03"),
        Bounty(id=3, title="Lixo 3", val=10.0, dist=300, type="Vidro", dest="COOPLUM", img="", lat=-9.64, lng=-35.71, created_at="2026-05-02"),
    ]


@pytest.mark.parametrize("sort_fn", [bubble_sort, insertion_sort, selection_sort, quick_sort])
def test_all_sorting_algorithms_correctness(sort_fn):
    # Caso padrão aleatório
    arr = [42, 17, 99, 13, 55, 8, 23, 13, 100, -5]
    sorted_res, metrics = sort_fn(arr)
    assert sorted_res == sorted(arr)
    assert metrics.size == len(arr)
    assert metrics.comparisons > 0
    assert metrics.execution_time_ms >= 0.0

    # Ordem decrescente
    sorted_rev, _ = sort_fn(arr, reverse=True)
    assert sorted_rev == sorted(arr, reverse=True)


@pytest.mark.parametrize("sort_fn", [bubble_sort, insertion_sort, selection_sort, quick_sort])
def test_sorting_algorithms_edge_cases(sort_fn):
    # Lista vazia
    res_empty, m_empty = sort_fn([])
    assert res_empty == []
    assert m_empty.size == 0

    # Lista com 1 elemento
    res_one, m_one = sort_fn([42])
    assert res_one == [42]
    assert m_one.size == 1

    # Lista já ordenada
    arr_sorted = [1, 2, 3, 4, 5, 6, 7]
    res_sorted, _ = sort_fn(arr_sorted)
    assert res_sorted == arr_sorted

    # Lista invertida
    arr_rev = [7, 6, 5, 4, 3, 2, 1]
    res_rev, _ = sort_fn(arr_rev)
    assert res_rev == [1, 2, 3, 4, 5, 6, 7]

    # Lista com todos os elementos iguais
    arr_eq = [5, 5, 5, 5, 5]
    res_eq, _ = sort_fn(arr_eq)
    assert res_eq == arr_eq


def test_domain_sorting_functions(sample_bounties):
    # Ordenação por recompensa (maior primeiro)
    by_val = sort_bounties_by_reward(sample_bounties, method="quicksort", reverse=True)
    assert [b.val for b in by_val] == [80.0, 25.0, 10.0]

    # Ordenação por proximidade ao usuário (-9.66, -35.73)
    by_dist = sort_bounties_by_distance(sample_bounties, user_lat=-9.66, user_lng=-35.73, method="quicksort")
    assert by_dist[0].id == 1  # Distância zero/mínima

    # Ordenação por urgência (mais recente primeiro)
    by_urg = sort_bounties_by_urgency(sample_bounties, method="quicksort", reverse=True)
    assert [b.id for b in by_urg] == [2, 3, 1]


def test_benchmark_runner_and_plot_generation(tmp_path):
    sizes = [20, 50, 100]
    data = benchmark_sorting_algorithms(sizes=sizes, repetitions=1)

    assert "Bubble Sort" in data
    assert "Insertion Sort" in data
    assert "Selection Sort" in data
    assert "QuickSort" in data

    for algo in data.values():
        assert len(algo["time_ms"]) == len(sizes)
        assert len(algo["comparisons"]) == len(sizes)

    # Gera gráfico e valida se o arquivo PNG é gravado fisicamente
    out_img = tmp_path / "test_benchmark.png"
    generated_path = plot_sorting_benchmark(data, sizes=sizes, output_path=str(out_img))
    assert Path(generated_path).exists()
    assert Path(generated_path).stat().st_size > 1000


def test_quicksort_large_duplicate_array():
    # Teste de regressão para RecursionError em arrays com muitas duplicatas
    large_duplicates = [42] * 1200
    sorted_res, metrics = quick_sort(large_duplicates)
    assert len(sorted_res) == 1200
    assert sorted_res == large_duplicates
    assert metrics.size == 1200

    pattern = [1, 2, 3] * 400
    sorted_pattern, _ = quick_sort(pattern)
    assert sorted_pattern == sorted(pattern)

