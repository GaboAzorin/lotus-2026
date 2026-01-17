"""
LOTO-2026 - Test Configuration and Fixtures
============================================

Shared fixtures for all test modules.
Run tests with: pytest tests/ -v
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
import pandas as pd
import numpy as np

# Add engine to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(PROJECT_ROOT, 'engine')
MODELS_DIR = os.path.join(ENGINE_DIR, 'models')
TOOLS_DIR = os.path.join(ENGINE_DIR, 'tools')

for path in [ENGINE_DIR, MODELS_DIR, TOOLS_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)


# ==============================================================================
# FIXTURES: Temporary directories and files
# ==============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Creates a temporary data directory with required structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    queue_dir = data_dir / "queue"
    queue_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_loto_csv(temp_data_dir):
    """Creates a sample LOTO CSV with realistic test data."""
    csv_path = temp_data_dir / "LOTO_HISTORIAL_MAESTRO.csv"

    # Generate 100 sample draws
    np.random.seed(42)
    rows = []
    for i in range(100):
        nums = sorted(np.random.choice(range(1, 42), size=6, replace=False))
        rows.append({
            'sorteo': 3800 + i,
            'fecha': f'2024-01-{(i % 28) + 1:02d} 21:00:00',
            'LOTO_n1': nums[0],
            'LOTO_n2': nums[1],
            'LOTO_n3': nums[2],
            'LOTO_n4': nums[3],
            'LOTO_n5': nums[4],
            'LOTO_n6': nums[5],
            'LOTO_comodin': np.random.randint(1, 42),
            'LOTO_pos1': nums[0],
            'LOTO_pos2': nums[1],
            'LOTO_pos3': nums[2],
            'LOTO_pos4': nums[3],
            'LOTO_pos5': nums[4],
            'LOTO_pos6': nums[5],
        })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_loto3_csv(temp_data_dir):
    """Creates a sample LOTO3 CSV with realistic test data."""
    csv_path = temp_data_dir / "LOTO3_MAESTRO.csv"

    np.random.seed(42)
    rows = []
    for i in range(100):
        rows.append({
            'sorteo': 13000 + i,
            'fecha': f'2024-01-{(i % 28) + 1:02d} 14:00:00',
            'n1': np.random.randint(0, 10),
            'n2': np.random.randint(0, 10),
            'n3': np.random.randint(0, 10),
        })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_simulaciones_csv(temp_data_dir):
    """Creates a sample LOTO_SIMULACIONES.csv for testing juez and entrenador."""
    csv_path = temp_data_dir / "LOTO_SIMULACIONES.csv"

    rows = []
    for i in range(20):
        rows.append({
            'id': 1000 + i,
            'fecha_generacion': f'2024-01-{(i % 28) + 1:02d} 10:00:00',
            'juego': 'LOTO',
            'numeros': str([1, 5, 10, 15, 20, 25]),
            'sorteo_objetivo': 3800 + i,
            'estado': 'AUDITADO' if i < 10 else 'PENDIENTE',
            'aciertos': i % 4,
            'score_afinidad': 10 + i * 2,
            'hora_dia': 21,
            'algoritmo': 'test_algo_v1',
        })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_genome_json(temp_data_dir):
    """Creates a sample loto_genome.json for testing."""
    json_path = temp_data_dir / "loto_genome.json"

    genome = {
        "algo_ranking": {
            "LOTO": {"test_algo_v1": 50.0, "oraculo_neural_v3": 45.0},
            "LOTO3": {"test_algo_v1": 30.0}
        },
        "morphology": {
            "LOTO": {
                "ideal_sum_range": [100, 180],
                "ideal_even_count": 3.0,
                "ideal_consecutivos": 0.5,
                "ideal_primos": 2.0
            }
        },
        "metadata": {
            "last_trained_id": 1000,
            "total_estudiados": 50,
            "updated_at": "2024-01-15 12:00:00"
        }
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2)

    return json_path


@pytest.fixture
def sample_queue_files(temp_data_dir):
    """Creates sample prediction JSON files in the queue directory."""
    queue_dir = temp_data_dir / "queue"
    files = []

    for i in range(3):
        filepath = queue_dir / f"prediccion_test_{i}.json"
        data = {
            'id': 2000 + i,
            'fecha_generacion': f'2024-01-15 10:0{i}:00',
            'juego': 'LOTO',
            'numeros': [1, 5, 10, 15, 20, 25 + i],
            'sorteo_objetivo': 3900,
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': 0.0,
            'hora_dia': 10,
            'algoritmo': 'test_consensus',
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        files.append(filepath)

    return files


# ==============================================================================
# FIXTURES: Mock objects
# ==============================================================================

@pytest.fixture
def mock_game_config():
    """Returns the standard GAME_CONFIG for testing."""
    return {
        "LOTO": {
            "type": "SET",
            "max": 41,
            "min_val": 1,
            "n_balls": 6,
            "input_prefix": "LOTO_pos",
            "target_prefix": "LOTO_n",
        },
        "LOTO3": {
            "type": "POSITIONAL",
            "max": 9,
            "min_val": 0,
            "n_balls": 3,
            "input_prefix": "n",
            "target_prefix": "n",
        },
    }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def assert_valid_loto_numbers(numbers):
    """Assert that numbers are valid LOTO numbers."""
    assert len(numbers) == 6, f"Expected 6 numbers, got {len(numbers)}"
    assert all(1 <= n <= 41 for n in numbers), f"Numbers out of range: {numbers}"
    assert len(set(numbers)) == 6, f"Duplicate numbers: {numbers}"


def assert_valid_loto3_numbers(numbers):
    """Assert that numbers are valid LOTO3 numbers."""
    assert len(numbers) == 3, f"Expected 3 numbers, got {len(numbers)}"
    assert all(0 <= n <= 9 for n in numbers), f"Numbers out of range: {numbers}"
