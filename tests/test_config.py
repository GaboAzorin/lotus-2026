"""
Tests for engine/config.py
===========================

Tests the centralized configuration module.
"""

import pytest
import os
import json
import tempfile


class TestGameConfig:
    """Tests for GAME_CONFIG dictionary."""

    def test_game_config_has_all_games(self):
        """Verify all expected games are configured."""
        from config import GAME_CONFIG

        expected_games = ['LOTO', 'LOTO3', 'LOTO4', 'RACHA']
        for game in expected_games:
            assert game in GAME_CONFIG, f"Missing game: {game}"

    def test_game_config_loto_structure(self):
        """Verify LOTO configuration has required fields."""
        from config import GAME_CONFIG

        loto = GAME_CONFIG['LOTO']
        assert loto['type'] == 'SET'
        assert loto['max'] == 41
        assert loto['min_val'] == 1
        assert loto['n_balls'] == 6
        assert 'input_prefix' in loto
        assert 'target_prefix' in loto

    def test_game_config_loto3_structure(self):
        """Verify LOTO3 configuration has required fields."""
        from config import GAME_CONFIG

        loto3 = GAME_CONFIG['LOTO3']
        assert loto3['type'] == 'POSITIONAL'
        assert loto3['max'] == 9
        assert loto3['min_val'] == 0
        assert loto3['n_balls'] == 3


class TestHorarios:
    """Tests for HORARIOS dictionary."""

    def test_horarios_has_all_games(self):
        """Verify all games have schedule defined."""
        from config import HORARIOS

        expected_games = ['LOTO', 'LOTO3', 'LOTO4', 'RACHA']
        for game in expected_games:
            assert game in HORARIOS, f"Missing schedule for: {game}"

    def test_horarios_loto_schedule(self):
        """Verify LOTO schedule is correct (Tues, Thurs, Sun at 21:00)."""
        from config import HORARIOS

        loto = HORARIOS['LOTO']
        assert 'dias' in loto
        assert 'horas' in loto
        assert set(loto['dias']) == {1, 3, 6}  # Tue, Thu, Sun
        assert 21 in loto['horas']

    def test_horarios_loto3_daily(self):
        """Verify LOTO3 runs every day."""
        from config import HORARIOS

        loto3 = HORARIOS['LOTO3']
        assert set(loto3['dias']) == {0, 1, 2, 3, 4, 5, 6}


class TestMLConfig:
    """Tests for ML_CONFIG dictionary."""

    def test_ml_config_alpha(self):
        """Verify ALPHA is set to 0.15 (not 0.05)."""
        from config import ML_CONFIG

        assert ML_CONFIG['ALPHA'] == 0.15, "ALPHA should be 0.15 after audit fix"

    def test_ml_config_train_split(self):
        """Verify train split ratio is 80%."""
        from config import ML_CONFIG

        assert ML_CONFIG['TRAIN_SPLIT_RATIO'] == 0.8

    def test_ml_config_rf_params(self):
        """Verify Random Forest parameters exist."""
        from config import ML_CONFIG

        assert 'RF_ESTIMATORS' in ML_CONFIG
        assert 'RF_MAX_DEPTH' in ML_CONFIG
        assert 'RF_MIN_SAMPLES_LEAF' in ML_CONFIG


class TestPaths:
    """Tests for path configuration."""

    def test_project_root_exists(self):
        """Verify PROJECT_ROOT points to valid directory."""
        from config import PROJECT_ROOT

        assert os.path.isdir(PROJECT_ROOT)

    def test_data_dir_exists(self):
        """Verify DATA_DIR exists."""
        from config import DATA_DIR

        assert os.path.isdir(DATA_DIR)

    def test_files_dict_has_keys(self):
        """Verify FILES dictionary has expected keys."""
        from config import FILES

        expected_keys = [
            'LOTO_MAESTRO', 'LOTO3_MAESTRO', 'LOTO4_MAESTRO',
            'RACHA_MAESTRO', 'SIMULACIONES', 'GENOMA', 'DASHBOARD'
        ]
        for key in expected_keys:
            assert key in FILES, f"Missing file path: {key}"


class TestAtomicWrite:
    """Tests for atomic_json_write function."""

    def test_atomic_write_creates_file(self, tmp_path):
        """Test that atomic_json_write creates a valid JSON file."""
        from config import atomic_json_write

        filepath = tmp_path / "test.json"
        data = {"test": "value", "number": 42}

        result = atomic_json_write(str(filepath), data)

        assert result is True
        assert filepath.exists()

        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_atomic_write_overwrites(self, tmp_path):
        """Test that atomic_json_write safely overwrites existing file."""
        from config import atomic_json_write

        filepath = tmp_path / "test.json"

        # Write initial data
        atomic_json_write(str(filepath), {"version": 1})

        # Overwrite
        atomic_json_write(str(filepath), {"version": 2})

        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded['version'] == 2

    def test_atomic_write_handles_unicode(self, tmp_path):
        """Test that atomic_json_write handles unicode correctly."""
        from config import atomic_json_write

        filepath = tmp_path / "unicode.json"
        data = {"mensaje": "Prediccion exitosa"}

        result = atomic_json_write(str(filepath), data)

        assert result is True
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded['mensaje'] == "Prediccion exitosa"


class TestSafeJsonRead:
    """Tests for safe_json_read function."""

    def test_safe_read_returns_data(self, tmp_path):
        """Test that safe_json_read returns correct data."""
        from config import safe_json_read

        filepath = tmp_path / "test.json"
        data = {"key": "value"}

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        result = safe_json_read(str(filepath))
        assert result == data

    def test_safe_read_missing_file_returns_default(self, tmp_path):
        """Test that safe_json_read returns default for missing file."""
        from config import safe_json_read

        filepath = tmp_path / "nonexistent.json"
        result = safe_json_read(str(filepath), default={"empty": True})

        assert result == {"empty": True}

    def test_safe_read_corrupted_file_returns_default(self, tmp_path):
        """Test that safe_json_read handles corrupted JSON."""
        from config import safe_json_read

        filepath = tmp_path / "corrupted.json"
        with open(filepath, 'w') as f:
            f.write("{invalid json content")

        result = safe_json_read(str(filepath), default={})
        assert result == {}


class TestLogging:
    """Tests for logging configuration."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a configured logger."""
        from config import setup_logging
        import logging

        logger = setup_logging("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert len(logger.handlers) > 0


class TestPrimosSet:
    """Tests for PRIMOS_SET constant."""

    def test_primos_set_contains_primes(self):
        """Verify PRIMOS_SET contains correct prime numbers."""
        from config import PRIMOS_SET

        expected_primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}
        assert PRIMOS_SET == expected_primes

    def test_primos_covers_loto_range(self):
        """Verify PRIMOS_SET covers primes up to LOTO max (41)."""
        from config import PRIMOS_SET, GAME_CONFIG

        max_loto = GAME_CONFIG['LOTO']['max']
        assert max(PRIMOS_SET) <= max_loto
