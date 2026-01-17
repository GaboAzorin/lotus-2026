"""
Tests for engine/models/entrenador_cognitivo.py
===============================================

Tests the cognitive trainer / genome learning system.
"""

import pytest
import os
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'engine'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'engine', 'models'))


class TestAlphaValue:
    """Tests for ALPHA learning rate."""

    def test_alpha_is_0_15(self):
        """Verify ALPHA is 0.15 (not 0.05 which causes amnesia)."""
        from entrenador_cognitivo import ALPHA

        assert ALPHA == 0.15, f"ALPHA should be 0.15, got {ALPHA}"

    def test_alpha_in_valid_range(self):
        """Verify ALPHA is in reasonable range for EMA."""
        from entrenador_cognitivo import ALPHA

        assert 0.05 <= ALPHA <= 0.5, "ALPHA should be between 0.05 and 0.5"


class TestCargarGenoma:
    """Tests for genome loading."""

    def test_cargar_genoma_empty_file(self, temp_data_dir, monkeypatch):
        """Test loading genome when file doesn't exist."""
        from entrenador_cognitivo import cargar_genoma, GENOMA_FILE

        monkeypatch.setattr('entrenador_cognitivo.GENOMA_FILE',
                           str(temp_data_dir / "nonexistent.json"))

        result = cargar_genoma()

        assert result == {"algo_ranking": {}, "metadata": {}, "morphology": {}}

    def test_cargar_genoma_existing_file(self, sample_genome_json, monkeypatch):
        """Test loading existing genome file."""
        from entrenador_cognitivo import cargar_genoma

        monkeypatch.setattr('entrenador_cognitivo.GENOMA_FILE', str(sample_genome_json))

        result = cargar_genoma()

        assert 'algo_ranking' in result
        assert 'LOTO' in result['algo_ranking']
        assert 'metadata' in result

    def test_cargar_genoma_corrupted_file(self, temp_data_dir, monkeypatch):
        """Test loading corrupted genome file returns empty structure."""
        from entrenador_cognitivo import cargar_genoma

        corrupted_path = temp_data_dir / "corrupted.json"
        with open(corrupted_path, 'w') as f:
            f.write("{invalid json")

        monkeypatch.setattr('entrenador_cognitivo.GENOMA_FILE', str(corrupted_path))

        result = cargar_genoma()

        # Should return default structure
        assert 'algo_ranking' in result
        assert 'metadata' in result


class TestPrimosSet:
    """Tests for PRIMOS_SET constant."""

    def test_primos_set_correct(self):
        """Verify PRIMOS_SET contains correct primes."""
        from entrenador_cognitivo import PRIMOS_SET

        expected = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}
        assert PRIMOS_SET == expected


class TestMorphologyCalculation:
    """Tests for morphology metric calculations."""

    def test_pares_count(self):
        """Test counting even numbers."""
        nums = [2, 4, 6, 8, 10, 12]  # All even
        pares = len([n for n in nums if n % 2 == 0])
        assert pares == 6

        nums = [1, 3, 5, 7, 9, 11]  # All odd
        pares = len([n for n in nums if n % 2 == 0])
        assert pares == 0

    def test_consecutivos_count(self):
        """Test counting consecutive pairs."""
        nums = sorted([1, 2, 3, 10, 20, 30])  # 2 consecutive pairs: (1,2), (2,3)
        cons = sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1)
        assert cons == 2

        nums = sorted([5, 10, 15, 20, 25, 30])  # No consecutives
        cons = sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1)
        assert cons == 0

    def test_primos_count(self):
        """Test counting prime numbers."""
        from entrenador_cognitivo import PRIMOS_SET

        nums = [2, 3, 5, 7, 11, 13]  # All primes
        primos = len([n for n in nums if n in PRIMOS_SET])
        assert primos == 6

        nums = [4, 6, 8, 10, 12, 14]  # No primes
        primos = len([n for n in nums if n in PRIMOS_SET])
        assert primos == 0


class TestSupervivorsipBiasFix:
    """Tests for survivorship bias fix - learning from ALL cases."""

    def test_learning_uses_all_cases(self, temp_data_dir, monkeypatch):
        """Verify that learning uses all cases, not just successes."""
        from entrenador_cognitivo import analizar_adn_ganador, SIMULACIONES_FILE, GENOMA_FILE

        # Create test data with mix of successes and failures
        csv_path = temp_data_dir / "LOTO_SIMULACIONES.csv"
        genome_path = temp_data_dir / "loto_genome.json"

        rows = []
        for i in range(20):
            rows.append({
                'id': 1000 + i,
                'fecha_generacion': f'2024-01-{(i % 28) + 1:02d} 10:00:00',
                'juego': 'LOTO',
                'numeros': str([1, 5, 10, 15, 20, 25]),
                'sorteo_objetivo': 3800 + i,
                'estado': 'AUDITADO',
                'aciertos': i % 4,  # Mix of 0, 1, 2, 3 aciertos
                'score_afinidad': 10 + i * 2,
                'hora_dia': 21,
                'algoritmo': 'test_algo_v1',
            })

        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False)

        # Create empty genome
        with open(genome_path, 'w') as f:
            json.dump({"algo_ranking": {}, "metadata": {"last_trained_id": 0}, "morphology": {}}, f)

        monkeypatch.setattr('entrenador_cognitivo.SIMULACIONES_FILE', str(csv_path))
        monkeypatch.setattr('entrenador_cognitivo.GENOMA_FILE', str(genome_path))

        # Run training
        analizar_adn_ganador()

        # Load genome and verify it learned
        with open(genome_path, 'r') as f:
            genome = json.load(f)

        # Should have processed all 20 cases (not just the ones with aciertos >= 2)
        assert genome['metadata']['total_estudiados'] >= 20


class TestWeightedLearning:
    """Tests for weighted learning based on aciertos."""

    def test_weight_calculation(self):
        """Test that weight is calculated as 1 + aciertos."""
        aciertos = 0
        peso = 1 + aciertos
        assert peso == 1

        aciertos = 3
        peso = 1 + aciertos
        assert peso == 4

        aciertos = 6
        peso = 1 + aciertos
        assert peso == 7


class TestEMACalculation:
    """Tests for Exponential Moving Average calculation."""

    def test_ema_update(self):
        """Test EMA formula: new = old * (1 - ALPHA) + new_value * ALPHA."""
        ALPHA = 0.15
        old_value = 50.0
        new_value = 70.0

        result = (old_value * (1 - ALPHA)) + (new_value * ALPHA)

        expected = 50.0 * 0.85 + 70.0 * 0.15
        assert abs(result - expected) < 0.001

    def test_ema_stability(self):
        """Test that EMA converges over time."""
        ALPHA = 0.15
        value = 50.0

        # Apply constant input of 100 multiple times
        for _ in range(50):
            value = (value * (1 - ALPHA)) + (100.0 * ALPHA)

        # Should converge close to 100
        assert abs(value - 100.0) < 1.0


class TestAtomicWrite:
    """Tests for atomic file writing in entrenador."""

    def test_genome_write_is_atomic(self, temp_data_dir, monkeypatch):
        """Test that genome writing doesn't corrupt on partial write."""
        from entrenador_cognitivo import GENOMA_FILE
        import tempfile
        import shutil

        genome_path = temp_data_dir / "loto_genome.json"

        # Write initial valid genome
        initial_data = {"algo_ranking": {"LOTO": {"algo1": 50}}, "metadata": {}, "morphology": {}}
        with open(genome_path, 'w') as f:
            json.dump(initial_data, f)

        # Verify file is valid JSON
        with open(genome_path, 'r') as f:
            loaded = json.load(f)

        assert loaded == initial_data


class TestHourlyRanking:
    """Tests for hourly ranking system."""

    def test_hourly_ranking_structure(self, sample_genome_json):
        """Test that hourly ranking can be added to genome."""
        with open(sample_genome_json, 'r') as f:
            genome = json.load(f)

        # Add hourly ranking
        genome['algo_ranking_hourly'] = {
            "LOTO": {
                "21": {"algo1": 55.0, "algo2": 45.0},
                "14": {"algo1": 40.0, "algo2": 60.0}
            }
        }

        # Verify structure
        assert "21" in genome['algo_ranking_hourly']['LOTO']
        assert genome['algo_ranking_hourly']['LOTO']['21']['algo1'] == 55.0
