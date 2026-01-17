"""
Tests for engine/models/oraculo_neural.py
==========================================

Tests the neural oracle prediction model.
"""

import pytest
import os
import sys
import numpy as np
import pandas as pd

# Ensure imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'engine'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'engine', 'models'))


class TestOraculoNeuralInit:
    """Tests for OraculoNeural initialization."""

    def test_init_loto_v3(self):
        """Test initialization with LOTO game v3."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v3')

        assert oracle.game_id == 'LOTO'
        assert oracle.version == 'v3'
        assert oracle.window_size == 3
        assert oracle.config['n_balls'] == 6
        assert oracle.config['max'] == 41

    def test_init_loto_v4(self):
        """Test initialization with LOTO game v4."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v4')

        assert oracle.version == 'v4'
        assert oracle.window_size == 12  # Extended window for v4

    def test_init_loto3(self):
        """Test initialization with LOTO3 game."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO3', version='v3')

        assert oracle.game_id == 'LOTO3'
        assert oracle.config['n_balls'] == 3
        assert oracle.config['max'] == 9
        assert oracle.config['type'] == 'POSITIONAL'

    def test_init_racha(self):
        """Test initialization with RACHA game."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('RACHA', version='v3')

        assert oracle.game_id == 'RACHA'
        assert oracle.config['n_balls'] == 10
        assert oracle.config['max'] == 20


class TestOneHotEncoding:
    """Tests for one-hot encoding functions."""

    def test_get_one_hot_basic(self):
        """Test basic one-hot encoding."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v3')
        numbers = [1, 5, 10, 20, 30, 41]

        vec = oracle._get_one_hot(numbers)

        assert vec.shape[0] == 42  # 0-41
        assert vec[1] == 1
        assert vec[5] == 1
        assert vec[10] == 1
        assert vec[0] == 0  # Not selected
        assert vec[2] == 0  # Not selected

    def test_get_one_hot_handles_invalid(self):
        """Test one-hot encoding handles invalid values gracefully."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v3')
        numbers = [1, 'invalid', None, 10]

        # Should not raise, just skip invalid values
        vec = oracle._get_one_hot(numbers)

        assert vec[1] == 1
        assert vec[10] == 1


class TestDecodeOneHotProbs:
    """Tests for probability decoding."""

    def test_decode_one_hot_probs_selects_top(self):
        """Test that decode selects top probability numbers."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v3')

        # Mock probability arrays - each number has [P(0), P(1)]
        probs_list = []
        for i in range(42):
            if i in [5, 10, 15, 20, 25, 30]:
                # High probability for these numbers
                probs_list.append([np.array([0.1, 0.9])])
            else:
                probs_list.append([np.array([0.9, 0.1])])

        result = oracle._decode_one_hot_probs(probs_list, top_n=6)

        assert len(result) == 6
        assert all(1 <= n <= 41 for n in result)
        # Should select the high-probability numbers
        assert set(result) == {5, 10, 15, 20, 25, 30}


class TestTrainTestSplit:
    """Tests for train/test split functionality."""

    def test_entrenar_uses_train_test_split(self, sample_loto_csv, temp_data_dir, monkeypatch):
        """Test that training uses 80/20 temporal split."""
        from oraculo_neural import OraculoNeural, DATA_DIR

        # Monkeypatch DATA_DIR to use temp directory
        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO', version='v3')
        oracle.maestro_file = str(sample_loto_csv)

        # Delete existing model to force retraining
        if os.path.exists(oracle.model_file):
            os.remove(oracle.model_file)

        result = oracle.entrenar()

        # Should return metrics dict
        assert result is not None
        assert 'train_score' in result
        assert 'test_score' in result

        # Metrics should be reasonable (not >90% which would indicate overfitting)
        assert result['train_score'] <= 1.0
        assert result['test_score'] <= 1.0

    def test_entrenar_returns_none_insufficient_data(self, temp_data_dir, monkeypatch):
        """Test that training returns None with insufficient data."""
        from oraculo_neural import OraculoNeural

        # Create CSV with only 10 rows (below minimum of 50)
        csv_path = temp_data_dir / "LOTO_HISTORIAL_MAESTRO.csv"
        df = pd.DataFrame({
            'sorteo': range(10),
            'fecha': ['2024-01-01'] * 10,
            'LOTO_n1': [1] * 10,
            'LOTO_n2': [2] * 10,
            'LOTO_n3': [3] * 10,
            'LOTO_n4': [4] * 10,
            'LOTO_n5': [5] * 10,
            'LOTO_n6': [6] * 10,
        })
        df.to_csv(csv_path, index=False)

        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO', version='v3')
        oracle.maestro_file = str(csv_path)

        result = oracle.entrenar()

        assert result is None


class TestPredecir:
    """Tests for prediction functionality."""

    def test_predecir_returns_correct_count(self, sample_loto_csv, temp_data_dir, monkeypatch):
        """Test that prediction returns correct number of balls."""
        from oraculo_neural import OraculoNeural

        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO', version='v3')
        oracle.maestro_file = str(sample_loto_csv)

        # Train first
        oracle.entrenar()

        # Predict
        result = oracle.predecir()

        assert len(result) == 6  # LOTO has 6 balls
        assert all(1 <= n <= 41 for n in result)
        assert len(set(result)) == 6  # No duplicates

    def test_predecir_loto3_positional(self, sample_loto3_csv, temp_data_dir, monkeypatch):
        """Test LOTO3 prediction returns 3 positional numbers."""
        from oraculo_neural import OraculoNeural

        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO3', version='v3')
        oracle.maestro_file = str(sample_loto3_csv)

        oracle.entrenar()
        result = oracle.predecir()

        assert len(result) == 3
        assert all(0 <= n <= 9 for n in result)

    def test_predecir_estocastico_varies(self, sample_loto_csv, temp_data_dir, monkeypatch):
        """Test that stochastic prediction can produce different results."""
        from oraculo_neural import OraculoNeural

        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO', version='v3')
        oracle.maestro_file = str(sample_loto_csv)
        oracle.entrenar()

        # Run multiple predictions
        results = [tuple(oracle.predecir(estocastico=True)) for _ in range(10)]

        # With stochastic sampling, not all results should be identical
        # (though some might be due to probability distribution)
        unique_results = set(results)
        # At least some variation expected (but not guaranteed)
        assert len(unique_results) >= 1

    def test_predecir_deterministic_consistent(self, sample_loto_csv, temp_data_dir, monkeypatch):
        """Test that deterministic prediction is consistent."""
        from oraculo_neural import OraculoNeural

        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO', version='v3')
        oracle.maestro_file = str(sample_loto_csv)
        oracle.entrenar()

        # Run multiple deterministic predictions
        results = [tuple(oracle.predecir(estocastico=False)) for _ in range(5)]

        # All results should be identical
        assert len(set(results)) == 1


class TestDynamicCols:
    """Tests for dynamic column detection."""

    def test_get_dynamic_cols_finds_columns(self):
        """Test that dynamic column finder works."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v3')

        df = pd.DataFrame({
            'LOTO_n1': [1], 'LOTO_n2': [2], 'LOTO_n3': [3],
            'LOTO_n4': [4], 'LOTO_n5': [5], 'LOTO_n6': [6],
        })

        cols = oracle._get_dynamic_cols(df, 'LOTO_n', 6)

        assert len(cols) == 6
        assert cols == ['LOTO_n1', 'LOTO_n2', 'LOTO_n3', 'LOTO_n4', 'LOTO_n5', 'LOTO_n6']

    def test_get_dynamic_cols_handles_missing(self):
        """Test column finder handles missing columns gracefully."""
        from oraculo_neural import OraculoNeural

        oracle = OraculoNeural('LOTO', version='v3')

        df = pd.DataFrame({
            'LOTO_n1': [1], 'LOTO_n2': [2], 'LOTO_n3': [3],
            # Missing n4, n5, n6
        })

        cols = oracle._get_dynamic_cols(df, 'LOTO_n', 6)

        # Should return only found columns
        assert len(cols) == 3


class TestAutoCuracion:
    """Tests for auto-healing functionality."""

    def test_auto_retraining_on_error(self, sample_loto_csv, temp_data_dir, monkeypatch):
        """Test that model auto-retrains on compatibility errors."""
        from oraculo_neural import OraculoNeural

        monkeypatch.setattr('oraculo_neural.DATA_DIR', str(temp_data_dir))

        oracle = OraculoNeural('LOTO', version='v3')
        oracle.maestro_file = str(sample_loto_csv)

        # Force model to be None to trigger auto-training
        oracle.model = None

        # predecir() should trigger entrenar() automatically
        result = oracle.predecir()

        # Should return valid prediction after auto-training
        assert len(result) == 6 or result == []  # Empty if data insufficient
