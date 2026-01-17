import pandas as pd
import json
import os
import re
from datetime import datetime

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'loto_biometrics.json')

# Configuración de los universos de datos
UNIVERSOS = {
    "LOTO_FAMILIA": {"file": "LOTO_HISTORIAL_MAESTRO.csv", "mode": "prefix_scan"}, # Escanea LOTO_n1, REVANCHA_n1, etc.
    "LOTO3":        {"file": "LOTO3_MAESTRO.csv",          "mode": "simple", "prefix": "n", "cols": 3},
    "LOTO4":        {"file": "LOTO4_MAESTRO.csv",          "mode": "simple", "prefix": "n", "cols": 4},
    "RACHA":        {"file": "RACHA_MAESTRO.csv",          "mode": "simple", "prefix": "n", "cols": 10}
}

# Rangos de números válidos por juego para suavizado Laplace
RANGOS_JUEGO = {
    "LOTO": (1, 41),
    "RECARGADO": (1, 41),
    "REVANCHA": (1, 41),
    "DESQUITE": (1, 41),
    "AHORA_SI_QUE_SI": (1, 41),
    "JUBILAZO_1": (1, 41),
    "JUBILAZO_2": (1, 41),
    "LOTO3": (0, 9),
    "LOTO4": (1, 41),
    "RACHA": (1, 20)
}

# Suavizado Laplace: añade 1 a todos los conteos para evitar prob 0
LAPLACE_SMOOTHING = 1

def safe_int(x):
    try: return int(x)
    except: return None

def generar_biometria():
    print("🧬 INICIANDO GENERADOR BIOMÉTRICO...")
    
    biometrics = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": "LotoAI Biometrics v2.0"
        },
        "games": {}
    }

    total_sorteos = 0

    for nombre_universo, config in UNIVERSOS.items():
        csv_path = os.path.join(DATA_DIR, config['file'])
        if not os.path.exists(csv_path):
            print(f"   ⚠️ Saltando {nombre_universo}: No existe CSV")
            continue

        print(f"   📂 Procesando {config['file']}...")
        try:
            df = pd.read_csv(csv_path)
            total_sorteos += len(df)

            # --- MODO 1: ESCANEO DE PREFIJOS (Para el archivo Loto Maestro que tiene muchos juegos dentro) ---
            if config['mode'] == 'prefix_scan':
                games_found = {}
                for col in df.columns:
                    # Detectar columnas tipo "NOMBRE_n1", "NOMBRE_n2"
                    match = re.match(r'^(.+)_n(\d+)$', col)
                    if match:
                        game_subname = match.group(1) # Ej: LOTO, RECARGADO
                        pos = int(match.group(2))
                        if game_subname not in games_found: games_found[game_subname] = {}
                        games_found[game_subname][pos] = col
                
                # Procesar cada sub-juego encontrado
                for game, positions in games_found.items():
                    _procesar_juego(df, game, positions, biometrics)

            # --- MODO 2: SIMPLE (Para Loto3, 4, Racha que tienen n1, n2...) ---
            elif config['mode'] == 'simple':
                positions = {}
                for i in range(1, config['cols'] + 1):
                    col_name = f"{config.get('prefix', 'n')}{i}" # Ej: n1, n2...
                    if col_name in df.columns:
                        positions[i] = col_name
                
                if positions:
                    _procesar_juego(df, nombre_universo, positions, biometrics)

        except Exception as e:
            print(f"   ❌ Error en {nombre_universo}: {e}")

    # Guardar Metadata Global
    biometrics["metadata"]["total_sorteos_analizados"] = total_sorteos

    # Escribir JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(biometrics, f, indent=2)
    
    print(f"\n✅ CEREBRO SINCRONIZADO. Archivo guardado en: {OUTPUT_FILE}")

def _procesar_juego(df, game_name, positions_dict, biometrics_dict):
    """
    Auxiliar para calcular frecuencias con suavizado Laplace.

    MEJORAS v2.1:
    - Suavizado Laplace: +1 a todos los números para evitar prob 0
    - Normalización a pesos (probabilidades)
    - Incluye rango completo del juego
    """
    game_data = {
        "source_type": "MECHANICAL",
        "positions": {}
    }

    # Determinar rango de números para este juego
    rango = RANGOS_JUEGO.get(game_name, (1, 41))
    min_num, max_num = rango

    sorted_pos = sorted(positions_dict.keys())
    for pos in sorted_pos:
        col = positions_dict[pos]

        # Calcular frecuencias observadas
        counts_raw = df[col].dropna().apply(lambda x: int(x) if x >= min_num else None).dropna().value_counts().to_dict()

        # SUAVIZADO LAPLACE: añadir +1 a TODOS los números del rango
        counts_smooth = {}
        total_con_laplace = 0
        for num in range(min_num, max_num + 1):
            count = counts_raw.get(num, 0) + LAPLACE_SMOOTHING
            counts_smooth[num] = count
            total_con_laplace += count

        # NORMALIZACIÓN: convertir a pesos (probabilidades)
        weights = {}
        for num, count in counts_smooth.items():
            weights[str(num)] = round(count / total_con_laplace, 6)

        game_data["positions"][str(pos)] = {
            "col_name": col,
            "counts": {str(k): v for k, v in counts_smooth.items()},
            "weights": weights  # NUEVO: pesos normalizados listos para usar
        }

    biometrics_dict["games"][game_name] = game_data
    print(f"      🔹 {game_name}: {len(sorted_pos)} posiciones con suavizado Laplace.")

if __name__ == "__main__":
    generar_biometria()