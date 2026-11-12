"""Diferencial 3 do Projeto (2ª Unidade - Obrigatório): Algoritmos de Ordenação.

Implementa os 4 métodos clássicos de ordenação requeridos pela disciplina:
1. Método da Bolha (Bubble Sort) - O(N^2)
2. Inserção Direta (Insertion Sort) - O(N^2) no pior/médio, O(N) no melhor
3. Seleção Direta (Selection Sort) - O(N^2) comparações fixas
4. QuickSort (Partição com Mediana/Otimização) - O(N log N) médio

Inclui instrumentação completa de métricas (comparações, trocas, tempo em ms)
e integração com as entidades do EcoBounty (ordenação de bounties por recompensa,
distância do coletor e urgência).
"""
import copy
import math
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

T = TypeVar("T")


@dataclass
class SortMetrics:
    algorithm: str
    size: int
    execution_time_ms: float
    comparisons: int
    swaps: int


def _get_key_func(key: Optional[Callable[[T], Any]]) -> Callable[[T], Any]:
    if key is None:
        return lambda x: x
    return key


def bubble_sort(
    arr: List[T],
    key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False,
) -> Tuple[List[T], SortMetrics]:
    """Método da Bolha (Bubble Sort) com otimização de parada precoce."""
    items = list(arr)
    n = len(items)
    key_fn = _get_key_func(key)
    comparisons = 0
    swaps = 0

    t_start = time.perf_counter()
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            comparisons += 1
            left_val = key_fn(items[j])
            right_val = key_fn(items[j + 1])

            should_swap = (left_val < right_val) if reverse else (left_val > right_val)
            if should_swap:
                items[j], items[j + 1] = items[j + 1], items[j]
                swaps += 1
                swapped = True
        if not swapped:
            break
    t_end = time.perf_counter()

    metrics = SortMetrics(
        algorithm="Bubble Sort",
        size=n,
        execution_time_ms=(t_end - t_start) * 1000.0,
        comparisons=comparisons,
        swaps=swaps,
    )
    return items, metrics


def insertion_sort(
    arr: List[T],
    key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False,
) -> Tuple[List[T], SortMetrics]:
    """Método de Inserção Direta (Insertion Sort)."""
    items = list(arr)
    n = len(items)
    key_fn = _get_key_func(key)
    comparisons = 0
    swaps = 0

    t_start = time.perf_counter()
    for i in range(1, n):
        current_item = items[i]
        curr_key = key_fn(current_item)
        j = i - 1

        while j >= 0:
            comparisons += 1
            cand_key = key_fn(items[j])
            should_shift = (cand_key < curr_key) if reverse else (cand_key > curr_key)
            if should_shift:
                items[j + 1] = items[j]
                swaps += 1
                j -= 1
            else:
                break
        items[j + 1] = current_item
    t_end = time.perf_counter()

    metrics = SortMetrics(
        algorithm="Insertion Sort",
        size=n,
        execution_time_ms=(t_end - t_start) * 1000.0,
        comparisons=comparisons,
        swaps=swaps,
    )
    return items, metrics


def selection_sort(
    arr: List[T],
    key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False,
) -> Tuple[List[T], SortMetrics]:
    """Método de Seleção Direta (Selection Sort)."""
    items = list(arr)
    n = len(items)
    key_fn = _get_key_func(key)
    comparisons = 0
    swaps = 0

    t_start = time.perf_counter()
    for i in range(n):
        extreme_idx = i
        for j in range(i + 1, n):
            comparisons += 1
            cand_key = key_fn(items[j])
            curr_extreme = key_fn(items[extreme_idx])

            should_update = (cand_key > curr_extreme) if reverse else (cand_key < curr_extreme)
            if should_update:
                extreme_idx = j

        if extreme_idx != i:
            items[i], items[extreme_idx] = items[extreme_idx], items[i]
            swaps += 1
    t_end = time.perf_counter()

    metrics = SortMetrics(
        algorithm="Selection Sort",
        size=n,
        execution_time_ms=(t_end - t_start) * 1000.0,
        comparisons=comparisons,
        swaps=swaps,
    )
    return items, metrics


def quick_sort(
    arr: List[T],
    key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False,
) -> Tuple[List[T], SortMetrics]:
    """Método de Ordenação Rápida (QuickSort) com pivô mediano de três e partição em 3 vias (Dutch National Flag).

    Otimizado para lidar eficientemente com duplicatas em O(N) e eliminar estouro de pilha (RecursionError)
    por meio de recursão de cauda eliminada com limite O(log N) de profundidade.
    """
    items = list(arr)
    n = len(items)
    key_fn = _get_key_func(key)
    comparisons = 0
    swaps = 0

    def _qsort(low: int, high: int):
        nonlocal comparisons, swaps
        while low < high:
            # Mediana de 3 para mitigar pior caso em arrays ordenados ou invertidos
            mid = (low + high) // 2
            k_low = key_fn(items[low])
            k_mid = key_fn(items[mid])
            k_high = key_fn(items[high])
            if (k_low <= k_mid <= k_high) or (k_high <= k_mid <= k_low):
                p_idx = mid
            elif (k_mid <= k_low <= k_high) or (k_high <= k_low <= k_mid):
                p_idx = low
            else:
                p_idx = high

            # Coloca o pivô mediano na posição inicial 'low'
            items[low], items[p_idx] = items[p_idx], items[low]
            swaps += 1
            pivot_val = key_fn(items[low])

            # Partição em 3 vias (Dijkstra Dutch National Flag):
            # items[low..lt-1] < pivot (ou > se reverse)
            # items[lt..gt] == pivot
            # items[gt+1..high] > pivot (ou < se reverse)
            lt = low
            gt = high
            i = low + 1

            while i <= gt:
                comparisons += 1
                curr_val = key_fn(items[i])
                is_less = (curr_val > pivot_val) if reverse else (curr_val < pivot_val)
                is_greater = (curr_val < pivot_val) if reverse else (curr_val > pivot_val)

                if is_less:
                    items[lt], items[i] = items[i], items[lt]
                    swaps += 1
                    lt += 1
                    i += 1
                elif is_greater:
                    items[i], items[gt] = items[gt], items[i]
                    swaps += 1
                    gt -= 1
                else:
                    i += 1

            # Recurse no menor subproblema e itere no maior (garante profundidade <= log2(N))
            left_size = lt - 1 - low
            right_size = high - (gt + 1)

            if left_size < right_size:
                _qsort(low, lt - 1)
                low = gt + 1
            else:
                _qsort(gt + 1, high)
                high = lt - 1

    t_start = time.perf_counter()
    if n > 1:
        _qsort(0, n - 1)
    t_end = time.perf_counter()

    metrics = SortMetrics(
        algorithm="QuickSort",
        size=n,
        execution_time_ms=(t_end - t_start) * 1000.0,
        comparisons=comparisons,
        swaps=swaps,
    )
    return items, metrics


# Funções de ordenação aplicadas às regras de negócio do EcoBounty


def calculate_haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calcula a distância em quilômetros entre dois pontos geográficos."""
    r = 6371.0  # Raio da Terra em km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def sort_bounties_by_reward(bounties: List[Any], method: str = "quicksort", reverse: bool = True) -> List[Any]:
    """Ordena os bounties pelo valor de recompensa financeira (padrão: maior recompensa primeiro)."""
    sorters = {
        "bubble": bubble_sort,
        "insertion": insertion_sort,
        "selection": selection_sort,
        "quicksort": quick_sort,
    }
    sorter = sorters.get(method.lower(), quick_sort)
    sorted_list, _ = sorter(
        bounties,
        key=lambda b: getattr(b, "val", getattr(b, "reward", 0.0)),
        reverse=reverse,
    )
    return sorted_list



def sort_bounties_by_distance(
    bounties: List[Any],
    user_lat: float,
    user_lng: float,
    method: str = "quicksort",
) -> List[Any]:
    """Ordena os bounties pela proximidade geográfica em relação ao coletor (menor distância primeiro)."""
    sorters = {
        "bubble": bubble_sort,
        "insertion": insertion_sort,
        "selection": selection_sort,
        "quicksort": quick_sort,
    }
    sorter = sorters.get(method.lower(), quick_sort)

    def dist_key(b):
        b_lat = getattr(b, "lat", user_lat)
        b_lng = getattr(b, "lng", user_lng)
        return calculate_haversine_distance(user_lat, user_lng, b_lat, b_lng)

    sorted_list, _ = sorter(bounties, key=dist_key, reverse=False)
    return sorted_list


def sort_bounties_by_urgency(
    bounties: List[Any],
    method: str = "quicksort",
    reverse: bool = True,
) -> List[Any]:
    """Ordena os bounties por urgência / data de criação (padrão: mais recente primeiro)."""
    sorters = {
        "bubble": bubble_sort,
        "insertion": insertion_sort,
        "selection": selection_sort,
        "quicksort": quick_sort,
    }
    sorter = sorters.get(method.lower(), quick_sort)

    def urgency_key(b):
        return getattr(b, "created_at", "") or ""

    sorted_list, _ = sorter(bounties, key=urgency_key, reverse=reverse)
    return sorted_list



def benchmark_sorting_algorithms(
    sizes: Optional[List[int]] = None,
    repetitions: int = 3,
) -> Dict[str, Dict[str, List[float]]]:
    """Executa benchmark comparativo de desempenho com múltiplos tamanhos de entrada N."""
    if sizes is None:
        sizes = [50, 100, 250, 500, 1000]

    results: Dict[str, Dict[str, List[float]]] = {
        "Bubble Sort": {"time_ms": [], "comparisons": [], "swaps": []},
        "Insertion Sort": {"time_ms": [], "comparisons": [], "swaps": []},
        "Selection Sort": {"time_ms": [], "comparisons": [], "swaps": []},
        "QuickSort": {"time_ms": [], "comparisons": [], "swaps": []},
    }

    algorithms = [
        ("Bubble Sort", bubble_sort),
        ("Insertion Sort", insertion_sort),
        ("Selection Sort", selection_sort),
        ("QuickSort", quick_sort),
    ]

    for n in sizes:
        # Gera lista aleatória reproduzível
        rng = random.Random(42 + n)
        test_data = [rng.uniform(10.0, 500.0) for _ in range(n)]

        for name, algo_func in algorithms:
            total_time = 0.0
            total_comps = 0
            total_swaps = 0

            for _ in range(repetitions):
                data_copy = list(test_data)
                _, metrics = algo_func(data_copy)
                total_time += metrics.execution_time_ms
                total_comps += metrics.comparisons
                total_swaps += metrics.swaps

            results[name]["time_ms"].append(round(total_time / repetitions, 4))
            results[name]["comparisons"].append(round(total_comps / repetitions))
            results[name]["swaps"].append(round(total_swaps / repetitions))

    return results
