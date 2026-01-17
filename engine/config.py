"""
LOTO-2026 - Configuración Centralizada
AUDITORÍA v4: Eliminación de configuración dispersa

Este módulo centraliza toda la configuración del proyecto para evitar
inconsistencias y facilitar el mantenimiento.
"""

import os
import logging
from datetime import datetime

# ==============================================================================
# RUTAS BASE (Calculadas una sola vez)
# ==============================================================================
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODELS_DIR = os.path.join(CONFIG_DIR, 'models')
SCRAPERS_DIR = os.path.join(CONFIG_DIR, 'scrapers')
TOOLS_DIR = os.path.join(CONFIG_DIR, 'tools')
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')

# Asegurar que existen los directorios críticos
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(QUEUE_DIR, exist_ok=True)

# ==============================================================================
# ARCHIVOS DE DATOS
# ==============================================================================
FILES = {
    'LOTO_MAESTRO': os.path.join(DATA_DIR, 'LOTO_HISTORIAL_MAESTRO.csv'),
    'LOTO3_MAESTRO': os.path.join(DATA_DIR, 'LOTO3_MAESTRO.csv'),
    'LOTO4_MAESTRO': os.path.join(DATA_DIR, 'LOTO4_MAESTRO.csv'),
    'RACHA_MAESTRO': os.path.join(DATA_DIR, 'RACHA_MAESTRO.csv'),
    'SIMULACIONES': os.path.join(DATA_DIR, 'LOTO_SIMULACIONES.csv'),
    'GENOMA': os.path.join(DATA_DIR, 'loto_genome.json'),
    'BIOMETRICS': os.path.join(DATA_DIR, 'loto_biometrics.json'),
    'DASHBOARD': os.path.join(PROJECT_ROOT, 'dashboard_data.json'),
    'JUGADAS': os.path.join(DATA_DIR, 'LOTO_JUGADAS.csv'),
}

# ==============================================================================
# CONFIGURACIÓN DE JUEGOS (GAME_CONFIG UNIFICADO)
# ==============================================================================
GAME_CONFIG = {
    "LOTO": {
        "type": "SET",
        "max": 41,
        "min_val": 1,
        "n_balls": 6,
        "input_prefix": "LOTO_pos",
        "target_prefix": "LOTO_n",
        "csv": FILES['LOTO_MAESTRO'],
        "api_id": "5271",
        "start_draw": 3803,
        "algos_extra": True,
    },
    "LOTO3": {
        "type": "POSITIONAL",
        "max": 9,
        "min_val": 0,
        "n_balls": 3,
        "input_prefix": "n",
        "target_prefix": "n",
        "csv": FILES['LOTO3_MAESTRO'],
        "api_id": "2181",
        "start_draw": 12991,
        "algos_extra": False,
    },
    "LOTO4": {
        "type": "SET",
        "max": 25,
        "min_val": 1,
        "n_balls": 4,
        "input_prefix": "pos",
        "target_prefix": "n",
        "csv": FILES['LOTO4_MAESTRO'],
        "api_id": "5270",
        "start_draw": 4230,
        "algos_extra": False,
    },
    "RACHA": {
        "type": "SET",
        "max": 20,
        "min_val": 1,
        "n_balls": 10,
        "input_prefix": "pos",
        "target_prefix": "n",
        "csv": FILES['RACHA_MAESTRO'],
        "api_id": "5272",
        "start_draw": 2963,
        "algos_extra": False,
    }
}

# ==============================================================================
# HORARIOS DE SORTEOS (UNIFICADO)
# ==============================================================================
HORARIOS = {
    "LOTO":   {"dias": [1, 3, 6],       "horas": [21]},
    "LOTO3":  {"dias": [0,1,2,3,4,5,6], "horas": [14, 18, 21]},
    "LOTO4":  {"dias": [0,1,2,3,4,5,6], "horas": [14, 21]},
    "RACHA":  {"dias": [0,1,2,3,4,5,6], "horas": [15, 22]}
}

# ==============================================================================
# CONSTANTES DE ML/ENTRENAMIENTO
# ==============================================================================
ML_CONFIG = {
    # Train/Test Split
    'TRAIN_SPLIT_RATIO': 0.8,

    # Random Forest Hiperparámetros
    'RF_ESTIMATORS': 80,
    'RF_MAX_DEPTH': 8,
    'RF_MIN_SAMPLES_LEAF': 10,

    # Aprendizaje Incremental (EMA)
    'ALPHA': 0.15,  # Factor de aprendizaje para rankings

    # Validación Morfológica - Umbrales de desviación
    'MORPH_THRESHOLDS': {
        'LOTO3': 8,
        'LOTO4': 20,
        'RACHA': 30,
        'LOTO': 40
    },
}

# ==============================================================================
# CONFIGURACIÓN DE SCRAPERS
# ==============================================================================
SCRAPER_CONFIG = {
    # Rate limiting
    'REQUEST_DELAY_SECONDS': 0.5,  # Delay entre requests a Polla.cl
    'MAX_CONSECUTIVE_ERRORS': 5,

    # CSRF Token
    'TOKEN_REFRESH_MINUTES': 20,  # Revalidar token cada X minutos

    # Endpoints
    'API_URL': "https://www.polla.cl/es/get/draw/results",
    'BASE_URL': "https://www.polla.cl/es/view/resultados",

    # Google Sheets (jugadas externas)
    'GOOGLE_SHEET_CSV_URL': "https://docs.google.com/spreadsheets/d/e/2PACX-1vQnOXW1U2VkJdNw6DplTvNGb5R3Fc6yNPKuewnBqh9w9C01m9ht2N8dNi3C4oqvIyL6An-coGf0TjhR/pub?output=csv",
}

# ==============================================================================
# PRIMOS (Para validación morfológica)
# ==============================================================================
PRIMOS_SET = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}

# ==============================================================================
# TIMEZONE
# ==============================================================================
TIMEZONE = 'America/Santiago'

# ==============================================================================
# LOGGING CENTRALIZADO
# ==============================================================================
def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configura y retorna un logger con formato estándar.

    Args:
        name: Nombre del módulo (típicamente __name__)
        level: Nivel de logging (default: INFO)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


# ==============================================================================
# UTILIDADES DE ESCRITURA ATÓMICA
# ==============================================================================
import tempfile
import shutil
import json


def atomic_json_write(filepath: str, data: dict, indent: int = 2) -> bool:
    """
    Escribe JSON de forma atómica (write-temp-rename pattern).

    Args:
        filepath: Ruta del archivo destino
        data: Datos a serializar como JSON
        indent: Indentación del JSON

    Returns:
        True si la escritura fue exitosa, False en caso contrario
    """
    logger = setup_logging('config.atomic_write')
    tmp_path = None

    try:
        dir_name = os.path.dirname(filepath) or '.'
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix='.json',
            dir=dir_name,
            delete=False
        ) as tmp_file:
            json.dump(data, tmp_file, indent=indent, ensure_ascii=False)
            tmp_path = tmp_file.name

        # Rename atómico
        shutil.move(tmp_path, filepath)
        return True

    except Exception as e:
        logger.error(f"Error en escritura atómica de {filepath}: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False


def safe_json_read(filepath: str, default: dict = None) -> dict:
    """
    Lee JSON de forma segura con fallback.

    Args:
        filepath: Ruta del archivo
        default: Valor por defecto si hay error

    Returns:
        Contenido del JSON o default
    """
    if default is None:
        default = {}

    if not os.path.exists(filepath):
        return default

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger = setup_logging('config.safe_read')
        logger.warning(f"Error leyendo {filepath}: {e}. Usando default.")
        return default
