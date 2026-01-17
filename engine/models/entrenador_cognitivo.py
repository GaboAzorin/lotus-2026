import pandas as pd
import json
import os
import numpy as np
import ast
import sys
import logging
import tempfile
import shutil
from datetime import datetime, timedelta

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")

# --- AUDITORÍA v5: ALPHA DINÁMICO POR ALGORITMO ---
# Cada algoritmo aprende a velocidad diferente según su complejidad
ALPHA_DEFAULT = 0.15
ALPHA_DINAMICO = {
    'forense_biometrico_v1': 0.20,   # Simple, aprende rápido
    'gaussiano_tactico_v1': 0.18,
    'delta_tactico_v1': 0.18,
    'markov_chain_v1': 0.18,
    'oraculo_neural_v3': 0.10,       # Complejo, aprende lento
    'oraculo_neural_v4': 0.08,       # Muy complejo, aprende muy lento
    'consenso_meritocratico_v2': 0.15
}

# Set de Primos para validación morfológica (V4 expandida)
PRIMOS_SET = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}

# Límites físicos por juego para validación de integridad
LIMITES_FISICOS = {
    'LOTO': {'min_sum': 21, 'max_sum': 231, 'n_balls': 6, 'range': (1, 41)},
    'LOTO3': {'min_sum': 0, 'max_sum': 27, 'n_balls': 3, 'range': (0, 9)},
    'LOTO4': {'min_sum': 10, 'max_sum': 154, 'n_balls': 4, 'range': (1, 41)},
    'RACHA': {'min_sum': 55, 'max_sum': 145, 'n_balls': 10, 'range': (1, 20)}
}

def obtener_alpha(algoritmo):
    """Retorna el ALPHA específico para cada algoritmo."""
    return ALPHA_DINAMICO.get(algoritmo, ALPHA_DEFAULT)

def validar_integridad_genoma(genoma):
    """
    Valida que los valores del genoma estén dentro de límites físicos.
    Corrige automáticamente valores imposibles.
    Retorna True si hubo correcciones, False si todo estaba bien.
    """
    hubo_correcciones = False

    for juego, limites in LIMITES_FISICOS.items():
        if juego not in genoma.get('morphology', {}):
            continue

        morph = genoma['morphology'][juego]

        # Validar rango de suma
        if 'ideal_sum_range' in morph:
            rango = morph['ideal_sum_range']
            min_fisico = limites['min_sum']
            max_fisico = limites['max_sum']

            # Corregir si está fuera de límites
            if rango[0] < min_fisico:
                logger.warning(f"⚠️ {juego}: sum_range[0]={rango[0]} < mínimo físico {min_fisico}. Corrigiendo...")
                morph['ideal_sum_range'][0] = min_fisico
                hubo_correcciones = True
            if rango[1] > max_fisico:
                logger.warning(f"⚠️ {juego}: sum_range[1]={rango[1]} > máximo físico {max_fisico}. Corrigiendo...")
                morph['ideal_sum_range'][1] = max_fisico
                hubo_correcciones = True
            if rango[0] > rango[1]:
                logger.warning(f"⚠️ {juego}: sum_range invertido [{rango[0]}, {rango[1]}]. Corrigiendo...")
                morph['ideal_sum_range'] = [min(rango), max(rango)]
                hubo_correcciones = True

        # Validar even_count (no puede ser mayor que n_balls)
        if 'ideal_even_count' in morph:
            if morph['ideal_even_count'] > limites['n_balls']:
                logger.warning(f"⚠️ {juego}: even_count={morph['ideal_even_count']} > n_balls={limites['n_balls']}. Corrigiendo...")
                morph['ideal_even_count'] = limites['n_balls'] / 2
                hubo_correcciones = True

    return hubo_correcciones

def detectar_anomalias(df_nuevo, umbral_zscore=3.0):
    """
    Detecta filas con scores anómalos usando z-score.
    Retorna DataFrame sin anomalías y lista de IDs anómalos.
    """
    if 'score_afinidad' not in df_nuevo.columns or len(df_nuevo) < 10:
        return df_nuevo, []

    mean = df_nuevo['score_afinidad'].mean()
    std = df_nuevo['score_afinidad'].std()

    if std == 0:
        return df_nuevo, []

    df_nuevo['zscore'] = (df_nuevo['score_afinidad'] - mean) / std
    anomalias = df_nuevo[abs(df_nuevo['zscore']) > umbral_zscore]['id'].tolist()

    if anomalias:
        logger.warning(f"🚨 Detectadas {len(anomalias)} anomalías (z-score > {umbral_zscore}): {anomalias[:5]}...")

    df_limpio = df_nuevo[abs(df_nuevo['zscore']) <= umbral_zscore].drop(columns=['zscore'])
    return df_limpio, anomalias

def cargar_genoma():
    """Carga el estado actual de la inteligencia colectiva con manejo de excepciones."""
    if os.path.exists(GENOMA_FILE):
        try:
            with open(GENOMA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Validar estructura mínima
                if "algo_ranking" not in data: data["algo_ranking"] = {}
                if "morphology" not in data: data["morphology"] = {}
                if "metadata" not in data: data["metadata"] = {}
                return data
        except Exception as e:
            print(f"   ⚠️ Error leyendo genoma: {e}. Creando uno nuevo...")
    
    return {"algo_ranking": {}, "metadata": {}, "morphology": {}}

def analizar_adn_ganador():
    """
    Sincroniza el ranking de algoritmos y la morfología ideal basándose
    en los últimos sorteos auditados por el Juez (Aprendizaje Incremental).

    MEJORAS v5:
    - Validación de integridad del genoma
    - Detección de anomalías con z-score
    - ALPHA dinámico por algoritmo
    """
    print("\n" + "="*60)
    print("🧠 ENTRENADOR COGNITIVO v12.5: INICIANDO CICLO DE APRENDIZAJE")
    print("="*60)

    if not os.path.exists(SIMULACIONES_FILE):
        print("   ❌ CRÍTICO: No existe LOTO_SIMULACIONES.csv. El cerebro no tiene qué estudiar.")
        return

    # 1. Carga de Datos
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
    except Exception as e:
        print(f"   ❌ Error al abrir simulaciones: {e}")
        return

    genoma = cargar_genoma()

    # NUEVO: Validar integridad del genoma al inicio
    if validar_integridad_genoma(genoma):
        print("   🔧 Se corrigieron valores inválidos en el genoma.")

    # Determinamos desde dónde retomar el entrenamiento (Checkpoint)
    last_trained_id = genoma.get("metadata", {}).get("last_trained_id", 0)

    # Filtramos filas auditadas que el cerebro aún no ha procesado
    df_nuevo = df[(df['estado'] == 'AUDITADO') & (df['id'] > last_trained_id)].copy()

    if df_nuevo.empty:
        print(f"   💤 Checkpoint: {last_trained_id}. Sin casos nuevos para analizar.")
        return

    # NUEVO: Detectar y filtrar anomalías
    df_nuevo, anomalias = detectar_anomalias(df_nuevo)
    if anomalias:
        print(f"   🚨 Excluidas {len(anomalias)} predicciones anómalas del entrenamiento.")

    print(f"   📊 Analizando {len(df_nuevo)} nuevos hitos de rendimiento...")

    ranking_global = genoma["algo_ranking"]
    morph_global = genoma["morphology"]
    juegos_en_lote = df_nuevo['juego'].unique()

    # 2. PROCESAMIENTO POR JUEGO
    for juego_id in juegos_en_lote:
        print(f"\n   📍 Universo: {juego_id}")
        df_juego = df_nuevo[df_nuevo['juego'] == juego_id]
        
        # --- [A.1] RANKING GLOBAL (EMA) ---
        performance_lote = df_juego.groupby('algoritmo')['score_afinidad'].mean().to_dict()
        ranking_juego = ranking_global.get(juego_id, {})
        
        for algo, score_lote in performance_lote.items():
            score_antiguo = ranking_juego.get(algo, 1.0)
            # NUEVO: ALPHA dinámico por algoritmo
            alpha = obtener_alpha(algo)
            nuevo_valor = (score_antiguo * (1 - alpha)) + (score_lote * alpha)
            ranking_juego[algo] = round(float(nuevo_valor), 2)
        ranking_global[juego_id] = ranking_juego

        # --- [A.2] RANKING HORARIO (NIVEL 2: Sensibilidad Horaria) ---
        # Inicializamos la estructura si no existe en el genoma
        if "algo_ranking_hourly" not in genoma: genoma["algo_ranking_hourly"] = {}
        
        # Agrupamos los nuevos datos por hora y algoritmo
        perf_horaria = df_juego.groupby(['hora_dia', 'algoritmo'])['score_afinidad'].mean().unstack(fill_value=0).to_dict('index')
        
        rank_horario_juego = genoma["algo_ranking_hourly"].get(juego_id, {})

        for h, algos_en_hora in perf_horaria.items():
            h_key = str(h)
            ranking_h = rank_horario_juego.get(h_key, {})
            
            for algo, score_lote in algos_en_hora.items():
                if score_lote == 0: continue
                val_old = ranking_h.get(algo, 1.0)
                # NUEVO: ALPHA dinámico también para ranking horario
                alpha = obtener_alpha(algo)
                val_new = (val_old * (1 - alpha)) + (score_lote * alpha)
                ranking_h[algo] = round(float(val_new), 2)
                
                # Reporte de "Especialización Horaria"
                if abs(val_new - val_old) > 0.2:
                    print(f"      🕒 Especialidad {h_key}h | {algo}: {ranking_h[algo]}")
            
            rank_horario_juego[h_key] = ranking_h
        
        genoma["algo_ranking_hourly"][juego_id] = rank_horario_juego
        
        # --- [B] ESTUDIO MORFOLÓGICO (ADN - APRENDIZAJE COMPLETO) ---
        # AUDITORÍA v4: Aprender de TODOS los casos, no solo éxitos
        # El supervivorship bias ignoraba 99% de las predicciones que fallaron
        # Ahora usamos ponderación por aciertos para que los éxitos tengan más peso

        if not df_juego.empty:
            memoria_morf = morph_global.get(juego_id, {})
            
            def suavizar_metrica(clave, lista_valores, factor_novedad=0.1):
                if not lista_valores: return
                avg_lote = np.mean(lista_valores)
                val_old = memoria_morf.get(clave, -1)
                if val_old == -1:
                    memoria_morf[clave] = float(round(avg_lote, 2))
                else:
                    memoria_morf[clave] = float(round((val_old * (1 - factor_novedad)) + (avg_lote * factor_novedad), 2))

            # Contenedores de métricas CON PESOS por aciertos
            pares, cons, bajos, terms, primos, mult3, deltas, sumas = [], [], [], [], [], [], [], []
            pesos_samples = []  # AUDITORÍA v4: Ponderación por rendimiento

            for _, row in df_juego.iterrows():
                try:
                    nums = sorted(ast.literal_eval(row['numeros']))
                    aciertos = row.get('aciertos', 0)

                    # Peso basado en aciertos: 0 aciertos = peso 1, 6 aciertos = peso 7
                    peso = 1 + aciertos

                    sumas.extend([sum(nums)] * peso)
                    pares.extend([len([n for n in nums if n % 2 == 0])] * peso)
                    cons.extend([sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1)] * peso)

                    limit = 4 if juego_id == "LOTO3" else (10 if juego_id == "RACHA" else 21)
                    bajos.extend([len([n for n in nums if n <= limit])] * peso)
                    terms.extend([len(set([n % 10 for n in nums]))] * peso)
                    primos.extend([len([n for n in nums if n in PRIMOS_SET])] * peso)
                    mult3.extend([len([n for n in nums if n % 3 == 0])] * peso)
                    if len(nums) > 1:
                        deltas.extend([float(np.mean(np.diff(nums)))] * peso)
                except (ValueError, SyntaxError, TypeError) as e:
                    logger.debug(f"Error procesando fila para morfología: {e}")
                    continue

            # Actualización del Genoma
            if sumas:
                # Rango de suma ideal (Percentiles 25-75 corregidos)
                p25, p75 = np.percentile(sumas, [25, 75])
                old_range = memoria_morf.get("ideal_sum_range", [20, 200])
                memoria_morf["ideal_sum_range"] = [
                    int((old_range[0] * 0.9) + (p25 * 0.1)),
                    int((old_range[1] * 0.9) + (p75 * 0.1))
                ]

            suavizar_metrica("ideal_even_count", pares)
            suavizar_metrica("ideal_consecutivos", cons)
            suavizar_metrica("ideal_bajos_altos", bajos)
            suavizar_metrica("ideal_terminaciones", terms)
            suavizar_metrica("ideal_primos", primos)
            suavizar_metrica("ideal_multiples_3", mult3)
            suavizar_metrica("ideal_avg_delta", deltas)
            
            morph_global[juego_id] = memoria_morf
            print(f"      🧬 ADN Sincronizado para {juego_id}.")

    # 3. GUARDADO Y METADATA CON ESCRITURA ATÓMICA
    max_id = int(df_nuevo['id'].max())
    genoma["metadata"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    genoma["metadata"]["last_trained_id"] = max_id
    genoma["metadata"]["total_estudiados"] = genoma["metadata"].get("total_estudiados", 0) + len(df_nuevo)

    # AUDITORÍA v4: Escritura atómica para prevenir corrupción
    try:
        dir_name = os.path.dirname(GENOMA_FILE)
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix='.json',
            dir=dir_name,
            delete=False
        ) as tmp_file:
            json.dump(genoma, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = tmp_file.name
        shutil.move(tmp_path, GENOMA_FILE)
    except Exception as e:
        logger.error(f"Error guardando genoma: {e}")
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return

    logger.info(f"CEREBRO ACTUALIZADO (Checkpoint #{max_id})")

    # --- NIVEL 4: Actualización del Meta-Learner ---
    try:
        from meta_learner import MetaLearner
        ml = MetaLearner()
        ml.entrenar() 
    except Exception as e:
        print(f"   ⚠️ No se pudo actualizar el Meta-Learner: {e}")

if __name__ == "__main__":
    analizar_adn_ganador()