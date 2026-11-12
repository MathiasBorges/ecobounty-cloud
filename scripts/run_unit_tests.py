"""Script para execução da suíte completa de testes do EcoBounty com pytest programático."""
import os
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Força SIMULATION_MODE para testes rápidos offline
os.environ["ECOBOUNTY_SIMULATION_MODE"] = "true"

import pytest

if __name__ == "__main__":
    args = [
        "tests/test_catbox_storage.py",
        "tests/test_gemini_vision.py",
        "tests/test_google_auth_flow.py",
        "tests/test_auth.py",
        "tests/test_bounties.py",
        "tests/test_camera_auth_adaptive.py",
        "tests/test_data_structures.py",
        "tests/test_e2e_flow.py",
        "tests/test_firestore.py",
        "tests/test_gcp_cloud.py",
        "tests/test_graphs.py",
        "tests/test_hash_tables.py",
        "tests/test_reactive_and_edge_cases.py",
        "tests/test_sorting_algorithms.py",
        "tests/test_views.py",
        "tests/test_wallet.py",
        "-v",
        "--tb=short",
        "-p", "no:cov",
        "-p", "no:anyio",
    ]
    sys.exit(pytest.main(args))
