import pandas as pd
import numpy as np
import os
import joblib
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from datetime import datetime
import logging
import warnings

# [IMP-ML-002] Intento de importación de XGBoost
try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- CONFIGURACIÓN DE RUTAS ROBUSTA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

# --- CONFIGURACIÓN MAESTRA DEL MULTIVERSO ---
GAME_CONFIG = {
    "LOTO": {
        "type": "SET", "max": 41, "min_val": 1, "n_balls": 6,
        "input_prefix": "LOTO_pos", "target_prefix": "LOTO_n"
    },
    "LOTO4": {
        "type": "SET", "max": 23, "min_val": 1, "n_balls": 4,
        "input_prefix": "pos", "target_prefix": "n"
    },
    "RACHA": {
        "type": "SET", "max": 20, "min_val": 1, "n_balls": 10,
        "input_prefix": "pos", "target_prefix": "n"
    },
    "LOTO3": {
        "type": "POSITIONAL", "max": 9, "min_val": 0, "n_balls": 3,
        "input_prefix": "n", "target_prefix": "n"
    }
}

class OraculoNeural:
    def __init__(self, game_id="LOTO", version="v3"):
        self.game_id = game_id
        self.version = version
        self.config = GAME_CONFIG.get(game_id, GAME_CONFIG["LOTO"])
        
        # Archivos de modelo separados para evitar contaminación cruzada
        self.model_file = os.path.join(DATA_DIR, f'{game_id.lower()}_rf_{version}.pkl')
        self._set_maestro_path()

        # --- CONFIGURACIÓN DIFERENCIADA (AUDITORÍA v4) ---
        if version == "v4":
            self.window_size = 12  # Ventana extendida para capturar inercia física
            self.max_depth_override = 8 # Regularización para evitar el efecto memoria
            print(f"🔬 MODO FÍSICO v4 ACTIVADO (Window: {self.window_size})")
        else:
            self.window_size = 3   # v3 original
            self.max_depth_override = None
            print(f"🧠 MODO REGLAMENTO v3 ACTIVADO (Window: {self.window_size})")

        self.model = None
        self._racha_binary_mode = False  # Flag para RACHA con clasificación binaria

        if os.path.exists(self.model_file):
            try:
                self.model = joblib.load(self.model_file)
                # Validación de compatibilidad inmediata
                if hasattr(self.model, "estimators_"):
                    print(f"✅ Modelo {version} cargado exitosamente.")
                # [IMP-RACHA-001] Detectar si es modelo binario de RACHA
                # (no es MultiOutputClassifier, es clasificador simple)
                elif self.game_id == "RACHA" and hasattr(self.model, "predict_proba"):
                    print(f"✅ Modelo RACHA binario {version} cargado exitosamente.")
                    self._racha_binary_mode = True
            except Exception as e:
                print(f"⚠️ Error cargando {self.model_file}: {e}. Se requiere re-entrenamiento.")
                self.model = None

    def _set_maestro_path(self):
        """Mapeo dinámico de archivos de datos"""
        mapa = {
            "LOTO": 'LOTO_HISTORIAL_MAESTRO.csv',
            "LOTO3": 'LOTO3_MAESTRO.csv',
            "LOTO4": 'LOTO4_MAESTRO.csv',
            "RACHA": 'RACHA_MAESTRO.csv'
        }
        fname = mapa.get(self.game_id, f'{self.game_id}_MAESTRO.csv')
        self.maestro_file = os.path.join(DATA_DIR, fname)

    # --- ZONA DE MATEMÁTICAS Y DECODIFICACIÓN ---

    def _get_one_hot(self, numbers):
        """Vectorización para juegos tipo SET (One-Hot Encoding)"""
        size = self.config['max'] + 1
        vec = np.zeros(size, dtype=np.int8)
        for n in numbers:
            try:
                val = int(float(n))
                if 0 <= val < size: vec[val] = 1
            except (ValueError, TypeError) as e:
                logger.debug(f"Error convirtiendo número {n}: {e}")
        return vec

    def _decode_one_hot_probs(self, probs_list, top_n):
        """Estrategia v3: Selección por probabilidad independiente"""
        candidates = []
        for num_val, prob_arr in enumerate(probs_list):
            if len(prob_arr) > 0 and prob_arr[0].shape[0] > 1:
                prob_success = prob_arr[0][1] 
            else:
                prob_success = 0
            
            if self.config['min_val'] <= num_val <= self.config['max']:
                candidates.append((num_val, prob_success))
            
        candidates.sort(key=lambda x: x[1], reverse=True)
        return sorted([x[0] for x in candidates[:top_n]])

    def _muestreo_probabilistico(self, probs_list, top_n):
        """Estrategia v4: Muestreo estocástico para permitir 'sueños' variados"""
        candidates = []
        for num_val, prob_arr in enumerate(probs_list):
            # Extraer probabilidad de éxito (clase 1)
            prob_success = prob_arr[0][1] if (len(prob_arr) > 0 and prob_arr[0].shape[0] > 1) else 0.001
            
            if self.config['min_val'] <= num_val <= self.config['max']:
                candidates.append((num_val, prob_success))
        
        nums = [c[0] for c in candidates]
        p = [c[1] for c in candidates]
        
        # Normalización de suma unitaria para np.random.choice
        sum_p = sum(p)
        p = np.array(p) / (sum_p if sum_p > 0 else 1.0)
        
        try:
            seleccion = np.random.choice(nums, size=top_n, replace=False, p=p)
            return sorted([int(x) for x in seleccion])
        except (ValueError, IndexError) as e:
            # Fallback a decodificación determinista si el muestreo falla
            logger.debug(f"Muestreo estocástico falló, usando fallback: {e}")
            return self._decode_one_hot_probs(probs_list, top_n)

    def _get_dynamic_cols(self, df, prefix, count):
        """Búsqueda flexible de columnas en el DataFrame"""
        candidates = [f"{prefix}{i}" for i in range(1, count + 1)]
        available_cols = df.columns.tolist()
        final_cols = []
        
        for c in candidates:
            if c in available_cols:
                final_cols.append(c)
            else:
                simple_c = c.split('_')[-1]
                if simple_c in available_cols:
                    final_cols.append(simple_c)
        return final_cols

    # --- FEATURE ENGINEERING ---

    def _calcular_gaps(self, X_raw, current_idx):
        """
        [IMP-FEAT-004] Vector de Gaps (Recencia)
        Crea un vector donde cada posición representa cuántos sorteos han pasado
        desde que ese número salió por última vez.
        Esta es la variable más predictiva en sistemas mecánicos (ley del retorno a la media).
        """
        min_val = self.config['min_val']
        max_val = self.config['max']
        size = max_val - min_val + 1

        # Inicializamos con valor alto (nunca ha salido en la ventana analizada)
        gaps = np.full(size, current_idx, dtype=np.float32)

        # Recorremos el historial hacia atrás buscando la última aparición de cada número
        for sorteo_offset in range(current_idx):
            idx = current_idx - 1 - sorteo_offset
            if idx < 0:
                break

            draw = X_raw[idx]
            for num in draw:
                try:
                    val = int(float(num))
                    if min_val <= val <= max_val:
                        num_idx = val - min_val
                        # Solo actualizamos si aún no hemos encontrado este número
                        if gaps[num_idx] == current_idx:
                            gaps[num_idx] = sorteo_offset + 1  # +1 porque 0 significaría "salió en el último"
                except (ValueError, TypeError):
                    continue

        # Normalización: dividimos por el máximo gap posible para obtener valores entre 0 y 1
        max_gap = max(current_idx, 1)
        return (gaps / max_gap).tolist()

    def _calcular_deltas_promedio(self, X_raw, current_idx, lookback=3):
        """
        [IMP-FEAT-006] Deltas y Velocidad
        Calcula la diferencia promedio entre los números de los últimos 'lookback' sorteos.
        Captura la "velocidad" de cambio en los patrones numéricos.
        """
        if current_idx < lookback:
            return [0.0] * 3  # delta_min, delta_max, delta_avg

        deltas = []
        for i in range(current_idx - lookback, current_idx):
            if i < 0:
                continue
            draw = sorted([int(float(x)) for x in X_raw[i] if str(x).replace('.','').replace('-','').isdigit()])
            if len(draw) >= 2:
                # Diferencias consecutivas dentro de cada sorteo
                for j in range(len(draw) - 1):
                    deltas.append(draw[j+1] - draw[j])

        if not deltas:
            return [0.0, 0.0, 0.0]

        # Normalizamos por el rango máximo posible
        max_range = self.config['max'] - self.config['min_val']
        return [
            min(deltas) / max_range,  # delta_min
            max(deltas) / max_range,  # delta_max
            np.mean(deltas) / max_range  # delta_avg
        ]

    def _calcular_meta_features(self, X_raw, current_idx, lookback=5):
        """
        [IMP-FEAT-007] Meta-Features del Biométrico
        Calcula características de alto nivel que el generador_biometrico.py ya computa
        pero que no se pasaban al modelo: paridad_promedio, suma_total, terminacion_mas_frecuente.
        """
        if current_idx < 1:
            return [0.5, 0.5, 0]  # paridad, suma_normalizada, terminacion

        start_idx = max(0, current_idx - lookback)

        paridades = []
        sumas = []
        terminaciones = []

        for i in range(start_idx, current_idx):
            draw = [int(float(x)) for x in X_raw[i] if str(x).replace('.','').replace('-','').isdigit()]
            if not draw:
                continue

            # Paridad: proporción de números pares
            pares = sum(1 for n in draw if n % 2 == 0)
            paridades.append(pares / len(draw))

            # Suma total normalizada
            suma = sum(draw)
            max_suma = self.config['max'] * len(draw)
            sumas.append(suma / max_suma if max_suma > 0 else 0)

            # Terminaciones (dígito final)
            for n in draw:
                terminaciones.append(n % 10)

        paridad_promedio = np.mean(paridades) if paridades else 0.5
        suma_promedio = np.mean(sumas) if sumas else 0.5

        # Terminación más frecuente (one-hot simplificado: valor / 10)
        if terminaciones:
            from collections import Counter
            terminacion_freq = Counter(terminaciones).most_common(1)[0][0] / 10.0
        else:
            terminacion_freq = 0

        return [paridad_promedio, suma_promedio, terminacion_freq]

    # --- [IMP-RACHA-001] CLASIFICACIÓN BINARIA POR NÚMERO (NEGATIVE SELECTION) ---

    def _preparar_dataset_racha_binario(self, df):
        """
        [IMP-RACHA-001] Transformación del dataset para RACHA.
        En lugar de 1 fila por sorteo, creamos 20 filas (una por cada bola posible 1-20).

        Features por bola:
        - Recencia: cuántos sorteos han pasado desde que salió
        - Frecuencia en últimos 10/50/100 sorteos
        - ¿Salió en el sorteo anterior? (binario)
        - Día de la semana
        - Posición promedio cuando sale

        Target: 1 (Salió) o 0 (No salió)

        Esta arquitectura permite usar clasificación binaria para identificar
        los números que NO saldrán (Negative Selection).
        """
        n_balls = self.config['n_balls']  # 10 para RACHA
        max_num = self.config['max']       # 20 para RACHA
        min_num = self.config['min_val']   # 1 para RACHA

        target_cols = [f"n{i}" for i in range(1, n_balls + 1)]

        # Verificar que las columnas existen
        available = [c for c in target_cols if c in df.columns]
        if len(available) < n_balls:
            logger.warning(f"RACHA: Columnas insuficientes. Disponibles: {available}")
            return None, None

        df = df.sort_values('sorteo', ascending=True).reset_index(drop=True)
        df = df.dropna(subset=available)

        # Día de la semana
        if 'fecha' in df.columns:
            dias = pd.to_datetime(df['fecha'], errors='coerce').dt.dayofweek.fillna(0).astype(int).values
        else:
            dias = np.zeros(len(df), dtype=int)

        # Construir historial de apariciones por número
        X_all = []
        y_all = []

        lookback_min = 10  # Necesitamos al menos 10 sorteos de historia

        for i in range(lookback_min, len(df)):
            # Números que salieron en este sorteo
            sorteo_actual = set()
            for col in available:
                try:
                    val = int(float(df.iloc[i][col]))
                    sorteo_actual.add(val)
                except:
                    continue

            # Sorteo anterior
            sorteo_anterior = set()
            for col in available:
                try:
                    val = int(float(df.iloc[i-1][col]))
                    sorteo_anterior.add(val)
                except:
                    continue

            # Para cada número posible (1-20), crear una fila
            for num in range(min_num, max_num + 1):
                features = []

                # 1. Recencia: cuántos sorteos desde que salió por última vez
                recencia = 0
                for j in range(i-1, -1, -1):
                    found = False
                    for col in available:
                        try:
                            if int(float(df.iloc[j][col])) == num:
                                found = True
                                break
                        except:
                            continue
                    if found:
                        recencia = i - j - 1
                        break
                    recencia += 1
                features.append(recencia / max(i, 1))  # Normalizado

                # 2. Frecuencia en últimos 10 sorteos
                freq_10 = 0
                for j in range(max(0, i-10), i):
                    for col in available:
                        try:
                            if int(float(df.iloc[j][col])) == num:
                                freq_10 += 1
                                break
                        except:
                            continue
                features.append(freq_10 / 10)

                # 3. Frecuencia en últimos 50 sorteos
                freq_50 = 0
                for j in range(max(0, i-50), i):
                    for col in available:
                        try:
                            if int(float(df.iloc[j][col])) == num:
                                freq_50 += 1
                                break
                        except:
                            continue
                features.append(freq_50 / 50)

                # 4. Frecuencia en últimos 100 sorteos
                freq_100 = 0
                for j in range(max(0, i-100), i):
                    for col in available:
                        try:
                            if int(float(df.iloc[j][col])) == num:
                                freq_100 += 1
                                break
                        except:
                            continue
                features.append(freq_100 / 100)

                # 5. ¿Salió en el sorteo anterior? (binario)
                features.append(1 if num in sorteo_anterior else 0)

                # 6. Día de la semana (normalizado)
                features.append(dias[i] / 6)

                # 7. Número normalizado (posición en el rango)
                features.append((num - min_num) / (max_num - min_num))

                # 8. Paridad del número
                features.append(num % 2)

                X_all.append(features)

                # Target: ¿Salió este número en el sorteo actual?
                y_all.append(1 if num in sorteo_actual else 0)

        return np.array(X_all), np.array(y_all)

    def _entrenar_racha_binario(self, df):
        """
        [IMP-RACHA-002] Entrena modelo de clasificación binaria para RACHA.
        Estrategia: Identificar los números que NO saldrán (Negative Selection).
        """
        logger.info("🎯 RACHA: Usando estrategia de Clasificación Binaria (Negative Selection)")

        X, y = self._preparar_dataset_racha_binario(df)
        if X is None:
            return None

        logger.info(f"   Dataset transformado: {len(X)} muestras ({len(X)//20} sorteos x 20 números)")

        # Balance de clases: ~50% (10 salen de 20)
        positivos = np.sum(y)
        logger.info(f"   Balance: {positivos} positivos ({positivos/len(y):.1%}), {len(y)-positivos} negativos")

        # Split temporal
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Modelo binario (no MultiOutput)
        if XGB_AVAILABLE:
            logger.info("   🚀 Usando XGBoost para clasificación binaria")
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                min_child_weight=10,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='binary:logistic',
                eval_metric='logloss',
                use_label_encoder=False,
                n_jobs=-1,
                random_state=42,
                verbosity=0
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_leaf=20,
                class_weight='balanced',
                n_jobs=-1,
                random_state=42
            )

        self.model.fit(X_train, y_train)

        # Métricas
        train_acc = self.model.score(X_train, y_train)
        test_acc = self.model.score(X_test, y_test)

        logger.info(f"   📊 Accuracy - Train: {train_acc:.3f}, Test: {test_acc:.3f}")

        # Guardar modelo
        joblib.dump(self.model, self.model_file, compress=9)
        logger.info(f"   Modelo RACHA binario guardado en {os.path.basename(self.model_file)}")

        # Marcar que este modelo usa el modo binario
        self._racha_binary_mode = True

        return {'train_score': train_acc, 'test_score': test_acc}

    def _predecir_racha_binario(self, df):
        """
        [IMP-RACHA-002] Predicción usando Negative Selection.
        Predecimos la probabilidad de cada número (1-20) y seleccionamos los 10 más probables.
        """
        n_balls = self.config['n_balls']
        max_num = self.config['max']
        min_num = self.config['min_val']

        target_cols = [f"n{i}" for i in range(1, n_balls + 1)]
        available = [c for c in target_cols if c in df.columns]

        df = df.sort_values('sorteo', ascending=True).reset_index(drop=True)

        # Último sorteo conocido (para calcular features)
        last_idx = len(df) - 1

        # Día objetivo
        if 'fecha' in df.columns:
            dia = pd.to_datetime(df.iloc[last_idx]['fecha'], errors='coerce')
            target_dow = dia.weekday() if pd.notna(dia) else datetime.now().weekday()
        else:
            target_dow = datetime.now().weekday()

        # Sorteo anterior
        sorteo_anterior = set()
        for col in available:
            try:
                val = int(float(df.iloc[last_idx][col]))
                sorteo_anterior.add(val)
            except:
                continue

        # Generar features para cada número
        predictions = []

        for num in range(min_num, max_num + 1):
            features = []

            # 1. Recencia
            recencia = 0
            for j in range(last_idx, -1, -1):
                found = False
                for col in available:
                    try:
                        if int(float(df.iloc[j][col])) == num:
                            found = True
                            break
                    except:
                        continue
                if found:
                    recencia = last_idx - j
                    break
                recencia += 1
            features.append(recencia / max(last_idx + 1, 1))

            # 2-4. Frecuencias
            for lookback in [10, 50, 100]:
                freq = 0
                for j in range(max(0, last_idx + 1 - lookback), last_idx + 1):
                    for col in available:
                        try:
                            if int(float(df.iloc[j][col])) == num:
                                freq += 1
                                break
                        except:
                            continue
                features.append(freq / lookback)

            # 5. ¿Salió en el último?
            features.append(1 if num in sorteo_anterior else 0)

            # 6. Día
            features.append(target_dow / 6)

            # 7. Número normalizado
            features.append((num - min_num) / (max_num - min_num))

            # 8. Paridad
            features.append(num % 2)

            # Predecir probabilidad
            X_num = np.array([features])
            if hasattr(self.model, 'predict_proba'):
                prob = self.model.predict_proba(X_num)[0][1]  # Prob de clase 1 (saldrá)
            else:
                prob = self.model.predict(X_num)[0]

            predictions.append((num, prob))

        # Ordenar por probabilidad descendente y tomar los 10 más probables
        predictions.sort(key=lambda x: x[1], reverse=True)

        # Log de predicciones con probabilidades
        logger.info("   🎲 RACHA Negative Selection - Probabilidades:")
        for num, prob in predictions[:10]:
            logger.info(f"      #{num}: {prob:.1%}")

        resultado = sorted([p[0] for p in predictions[:n_balls]])
        return resultado

    def _calcular_mapa_calor(self, X_raw, current_idx, lookback=10):
        """
        Calcula la frecuencia normalizada de cada número en los últimos 'lookback' sorteos.
        Retorna un vector de probabilidades de tamaño (max_val - min_val + 1).
        """
        min_val = self.config['min_val']
        max_val = self.config['max']
        size = max_val - min_val + 1
        
        counts = np.zeros(size)
        
        # Tomamos los últimos 'lookback' sorteos ANTERIORES a current_idx
        start_idx = max(0, current_idx - lookback)
        history = X_raw[start_idx:current_idx]
        
        for draw in history:
            for num in draw:
                try:
                    val = int(float(num))
                    if min_val <= val <= max_val:
                        counts[val - min_val] += 1
                except:
                    continue
        
        # Normalización
        total = np.sum(counts)
        if total > 0:
            return (counts / total).tolist()
        return counts.tolist()

    # --- PREPARACIÓN DE DATOS (EL CORAZÓN DE LA CIRUGÍA) ---

    def _preparar_dataset(self, df):
        n_balls = self.config['n_balls']
        
        # 1. Definir Input (Física) y Target (Depende de Versión)
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        
        if self.version == "v4":
            # CIRUGÍA #3: v4 aprende la trayectoria (pos -> pos)
            target_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
            target_type = 'POSITIONAL' 
            print(f"🧪 v4: Entrenando Trayectoria Física ({len(target_cols)} cols)")
        else:
            # v3 sigue con el Reglamento (pos -> n)
            target_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
            target_type = self.config['type']
            print(f"📜 v3: Entrenando Reglamento ({len(target_cols)} cols)")

        # 2. Validación de Integridad Estricta
        if len(input_cols) < n_balls:
            input_cols = target_cols 
            
        if len(target_cols) < n_balls:
            print(f"❌ Error: Columnas insuficientes para {self.game_id}")
            return None, None, None, None
            
        # 3. Limpieza y Ordenamiento
        df = df.sort_values('sorteo', ascending=True).reset_index(drop=True)
        df = df.dropna(subset=input_cols + target_cols)
        
        X_raw = df[input_cols].values 
        y_raw = df[target_cols].values 
        
        # Feature Contextual: Día de la semana
        if 'fecha' in df.columns:
            dias = pd.to_datetime(df['fecha'], errors='coerce').dt.dayofweek.fillna(0).astype(int).values
        else:
            dias = np.zeros(len(df), dtype=int)

        X, y = [], []
        
        # 4. Construcción de Ventanas Deslizantes
        for i in range(self.window_size, len(df)):
            features = []
            for w in range(1, self.window_size + 1):
                features.extend(X_raw[i-w])

            features.append(dias[i])

            # [IMP-FEAT-001] Inyección de Rachas (Mapa de Calor)
            # Analizamos los 10 sorteos previos a 'i'
            heat_map = self._calcular_mapa_calor(X_raw, i, lookback=10)
            features.extend(heat_map)

            # [IMP-FEAT-004] Vector de Gaps (Recencia) - EL ESLABÓN PERDIDO
            gaps = self._calcular_gaps(X_raw, i)
            features.extend(gaps)

            # [IMP-FEAT-006] Deltas Promedio (Velocidad)
            deltas = self._calcular_deltas_promedio(X_raw, i, lookback=3)
            features.extend(deltas)

            # [IMP-FEAT-007] Meta-Features del Biométrico
            meta_features = self._calcular_meta_features(X_raw, i, lookback=5)
            features.extend(meta_features)

            X.append(features)
            
            if target_type == 'SET':
                y.append(self._get_one_hot(y_raw[i]))
            else:
                # v4 y Loto3 entran aquí: predicción de valores exactos vinculados
                y.append([int(float(v)) for v in y_raw[i]])
                
        return np.array(X), np.array(y), input_cols, target_cols

    # --- ENTRENAMIENTO ADAPTATIVO ---

    def entrenar(self, sorteo_limite=None):
        """
        Entrena el modelo con train/test split temporal (80/20).
        AUDITORÍA v4: Previene overfitting y proporciona métricas realistas.
        [IMP-RACHA-001] RACHA ahora usa clasificación binaria (Negative Selection).
        """
        msg = f" (Sorteo límite: #{sorteo_limite})" if sorteo_limite else " (Toda la historia)"
        logger.info(f"ORÁCULO {self.version}: Iniciando entrenamiento para {self.game_id}{msg}")

        if not os.path.exists(self.maestro_file):
            logger.error(f"Archivo maestro no encontrado: {self.maestro_file}")
            return

        df = pd.read_csv(self.maestro_file)
        if sorteo_limite is not None and 'sorteo' in df.columns:
            df = df[df['sorteo'] <= int(sorteo_limite)]

        if len(df) < 50:
            logger.warning(f"Datos insuficientes ({len(df)} filas). Mínimo 50.")
            return

        # [IMP-RACHA-001] RACHA usa estrategia especial de Clasificación Binaria
        if self.game_id == "RACHA":
            return self._entrenar_racha_binario(df)

        X, y, _, _ = self._preparar_dataset(df)
        if X is None: return

        samples = len(X)

        # --- AUDITORÍA v4: VALIDACIÓN CRUZADA TEMPORAL ---
        # [IMP-ML-008] Implementación de TimeSeriesSplit (5 folds)
        logger.info(f"   Iniciando Validación Cruzada Temporal (5 folds)...")
        tscv = TimeSeriesSplit(n_splits=5)
        
        cv_scores_train = []
        cv_scores_test = []
        
        # Iteramos sobre los folds para recolectar métricas robustas
        for fold, (train_index, test_index) in enumerate(tscv.split(X)):
            X_fold_train, X_fold_test = X[train_index], X[test_index]
            y_fold_train, y_fold_test = y[train_index], y[test_index]
            
            # Usamos modelo base para evaluación rápida
            temp_model = self._build_model()
            temp_model.fit(X_fold_train, y_fold_train)
            
            s_train = temp_model.score(X_fold_train, y_fold_train)
            s_test = temp_model.score(X_fold_test, y_fold_test)
            
            cv_scores_train.append(s_train)
            cv_scores_test.append(s_test)
            logger.info(f"      Fold {fold+1}: Train={s_train:.3f}, Test={s_test:.3f}")

        avg_train = np.mean(cv_scores_train)
        avg_test = np.mean(cv_scores_test)
        logger.info(f"   📊 CV Promedio (5 folds) - Train: {avg_train:.3f}, Test: {avg_test:.3f}")

        # --- ENTRENAMIENTO FINAL ---
        # Mantenemos el split 80/20 para la fase de optimización y guardado
        split_idx = int(samples * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        logger.info(f"   Split final (Optimización): Train={len(X_train)}, Test={len(X_test)}")

        # [IMP-ML-003] Optimización de Hiperparámetros (GridSearchCV)
        # Solo ejecutamos GridSearch si tenemos suficientes datos para validar
        if len(X_train) > 100:
            logger.info("   🔍 Iniciando GridSearchCV para encontrar hiperparámetros óptimos...")
            
            # Espacio de búsqueda optimizado para series temporales ruidosas
            param_grid = {
                'estimator__n_estimators': [50, 100, 150],
                'estimator__max_depth': [3, 5, 8],
                'estimator__min_samples_leaf': [10, 20, 30]
            }

            # TimeSeriesSplit para validación cruzada interna (evita mirar al futuro)
            tscv = TimeSeriesSplit(n_splits=3)
            
            base_rf = RandomForestClassifier(
                random_state=42, 
                max_features='sqrt',
                class_weight='balanced' if (self.version == "v3" and self.config['type'] == 'SET') else None,
                n_jobs=-1
            )
            
            model_wrapper = MultiOutputClassifier(base_rf)
            
            grid_search = GridSearchCV(
                estimator=model_wrapper,
                param_grid=param_grid,
                cv=tscv,
                n_jobs=-1,
                verbose=1
            )
            
            try:
                grid_search.fit(X_train, y_train)
                logger.info(f"   🏆 Mejores parámetros: {grid_search.best_params_}")
                self.model = grid_search.best_estimator_
            except Exception as e:
                logger.warning(f"   ⚠️ Falló GridSearchCV ({e}), usando configuración manual por defecto.")
                # Fallback a configuración manual si GridSearch falla
                self._entrenar_manual(X_train, y_train)
        else:
            logger.info("   ⚠️ Datos insuficientes para GridSearch, usando configuración manual.")
            self._entrenar_manual(X_train, y_train)

        # --- MÉTRICAS DE EVALUACIÓN REALISTAS ---
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        # Alerta si hay overfitting severo (para lotería, train > 0.5 ya es sospechoso)
        if train_score > 0.5 and test_score < 0.15:
            logger.warning(f"   ALERTA CRÍTICA: Overfitting severo detectado - Train: {train_score:.3f}, Test: {test_score:.3f}. El modelo puede estar memorizando ruido.")
        else:
            logger.info(f"   Metrics - Train: {train_score:.3f}, Test: {test_score:.3f}")

        # Para lotería, esperamos accuracy muy baja (<10% es realista)
        if test_score > 0.3:
            logger.warning(f"   SOSPECHA: Test accuracy demasiado alta ({test_score:.3f}). Revisar data leakage.")

        # Guardado con alta compresión (ANTES de métricas para no perder el modelo)
        joblib.dump(self.model, self.model_file, compress=9)
        logger.info(f"Modelo {self.version} guardado en {os.path.basename(self.model_file)}")

        # --- MÉTRICAS ML EXTENDIDAS ---
        metrics = self._calcular_metricas_ml(X_train, y_train, X_test, y_test)
        logger.info(f"   📊 ML Metrics Report ({self.game_id} {self.version}):")
        logger.info(f"      [TRAIN] Accuracy: {metrics['train_accuracy']:.4f} | Precision: {metrics['train_precision']:.4f} | Recall: {metrics['train_recall']:.4f} | F1-Score: {metrics['train_f1']:.4f}")
        logger.info(f"      [TEST]  Accuracy: {metrics['test_accuracy']:.4f} | Precision: {metrics['test_precision']:.4f} | Recall: {metrics['test_recall']:.4f} | F1-Score: {metrics['test_f1']:.4f}")

        # --- [IMP-VAL-001] HIT RATE @ K (Métrica Real para Lotería) ---
        if self.config['type'] == 'SET':
            hit_rate_train, avg_hits_train = self._calcular_hit_rate_at_k(X_train, y_train, k=10)
            hit_rate_test, avg_hits_test = self._calcular_hit_rate_at_k(X_test, y_test, k=10)

            logger.info(f"   🎯 Hit Rate @ 10 (Métrica Real):")
            logger.info(f"      [TRAIN] Hit Rate: {hit_rate_train:.2%} | Avg Hits/Sorteo: {avg_hits_train:.2f}")
            logger.info(f"      [TEST]  Hit Rate: {hit_rate_test:.2%} | Avg Hits/Sorteo: {avg_hits_test:.2f}")

            # Contexto: para LOTO (6 de 41), azar puro = 6/41 = 14.6%
            # Para RACHA (10 de 20), azar puro = 50%
            azar = self.config['n_balls'] / self.config['max']
            if hit_rate_test > azar:
                logger.info(f"      ✅ Modelo SUPERA el azar ({azar:.1%})")
            else:
                logger.warning(f"      ⚠️ Modelo NO supera el azar ({azar:.1%})")

            metrics['hit_rate_train'] = hit_rate_train
            metrics['hit_rate_test'] = hit_rate_test
            metrics['avg_hits_train'] = avg_hits_train
            metrics['avg_hits_test'] = avg_hits_test

        return {
            'train_score': train_score,
            'test_score': test_score,
            **metrics  # Include all extended ML metrics
        }

    def _calcular_hit_rate_at_k(self, X, y, k=10):
        """
        [IMP-VAL-001] Hit Rate @ K
        Métrica más realista para lotería: de los K números que el modelo predijo
        con mayor probabilidad, ¿cuántos estaban realmente en el sorteo ganador?

        Esta métrica refleja el valor real del modelo. Si consistentemente metemos
        1-2 números ganadores en el Top K, ya tenemos ventaja sobre el azar.

        Args:
            X: Features de prueba
            y: Labels reales (one-hot encoded para SET)
            k: Cuántos números top considerar (default 10)

        Returns:
            hit_rate: Proporción promedio de aciertos en Top K
            avg_hits: Número promedio de aciertos por sorteo
        """
        if not hasattr(self.model, 'predict_proba'):
            return 0.0, 0.0

        try:
            probs = self.model.predict_proba(X)
        except Exception as e:
            logger.debug(f"predict_proba falló: {e}")
            return 0.0, 0.0

        total_hits = 0
        total_possible = 0

        for sample_idx in range(len(X)):
            # Extraer probabilidades para esta muestra
            sample_probs = []
            for num_val, prob_arr in enumerate(probs):
                if len(prob_arr) > 0 and prob_arr[sample_idx].shape[0] > 1:
                    prob_success = prob_arr[sample_idx][1]
                else:
                    prob_success = 0
                if self.config['min_val'] <= num_val <= self.config['max']:
                    sample_probs.append((num_val, prob_success))

            # Ordenar por probabilidad descendente y tomar Top K
            sample_probs.sort(key=lambda x: x[1], reverse=True)
            top_k_nums = set([x[0] for x in sample_probs[:k]])

            # Extraer números reales del sorteo
            if self.config['type'] == 'SET':
                # y es one-hot: los índices con valor 1 son los números que salieron
                real_nums = set([i for i, val in enumerate(y[sample_idx]) if val == 1])
            else:
                # y es lista de valores
                real_nums = set([int(v) for v in y[sample_idx]])

            # Contar hits
            hits = len(top_k_nums & real_nums)
            total_hits += hits
            total_possible += len(real_nums)

        if total_possible == 0:
            return 0.0, 0.0

        hit_rate = total_hits / total_possible
        avg_hits = total_hits / len(X) if len(X) > 0 else 0

        return hit_rate, avg_hits

    def _calcular_metricas_ml(self, X_train, y_train, X_test, y_test):
        """
        Calcula métricas ML extendidas: Accuracy, Precision, Recall, F1-Score.
        Soporta binary-multioutput (SET/one-hot) y multiclass-multioutput (POSITIONAL/v4).
        """
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        zero_div = 0

        # Intento 1: average='samples' (funciona para binary-multioutput)
        try:
            metrics = {
                'train_accuracy': accuracy_score(y_train, y_pred_train),
                'train_precision': precision_score(y_train, y_pred_train, average='samples', zero_division=zero_div),
                'train_recall': recall_score(y_train, y_pred_train, average='samples', zero_division=zero_div),
                'train_f1': f1_score(y_train, y_pred_train, average='samples', zero_division=zero_div),
                'test_accuracy': accuracy_score(y_test, y_pred_test),
                'test_precision': precision_score(y_test, y_pred_test, average='samples', zero_division=zero_div),
                'test_recall': recall_score(y_test, y_pred_test, average='samples', zero_division=zero_div),
                'test_f1': f1_score(y_test, y_pred_test, average='samples', zero_division=zero_div),
            }
            return metrics
        except ValueError:
            pass

        # Intento 2: Per-column metrics (para multiclass-multioutput)
        try:
            n_outputs = y_train.shape[1]

            # accuracy_score tampoco soporta multiclass-multioutput, calcular por columna
            train_acc = float(np.mean([
                accuracy_score(y_train[:, col], y_pred_train[:, col]) for col in range(n_outputs)]))
            test_acc = float(np.mean([
                accuracy_score(y_test[:, col], y_pred_test[:, col]) for col in range(n_outputs)]))

            col_metrics = {'precision': [], 'recall': [], 'f1': []}
            for col in range(n_outputs):
                col_metrics['precision'].append(
                    precision_score(y_train[:, col], y_pred_train[:, col], average='macro', zero_division=zero_div))
                col_metrics['recall'].append(
                    recall_score(y_train[:, col], y_pred_train[:, col], average='macro', zero_division=zero_div))
                col_metrics['f1'].append(
                    f1_score(y_train[:, col], y_pred_train[:, col], average='macro', zero_division=zero_div))

            col_metrics_test = {'precision': [], 'recall': [], 'f1': []}
            for col in range(n_outputs):
                col_metrics_test['precision'].append(
                    precision_score(y_test[:, col], y_pred_test[:, col], average='macro', zero_division=zero_div))
                col_metrics_test['recall'].append(
                    recall_score(y_test[:, col], y_pred_test[:, col], average='macro', zero_division=zero_div))
                col_metrics_test['f1'].append(
                    f1_score(y_test[:, col], y_pred_test[:, col], average='macro', zero_division=zero_div))

            metrics = {
                'train_accuracy': train_acc,
                'train_precision': float(np.mean(col_metrics['precision'])),
                'train_recall': float(np.mean(col_metrics['recall'])),
                'train_f1': float(np.mean(col_metrics['f1'])),
                'test_accuracy': test_acc,
                'test_precision': float(np.mean(col_metrics_test['precision'])),
                'test_recall': float(np.mean(col_metrics_test['recall'])),
                'test_f1': float(np.mean(col_metrics_test['f1'])),
            }
            return metrics
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudieron calcular métricas extendidas: {e}")
            return {
                'train_accuracy': 0.0, 'train_precision': 0.0, 'train_recall': 0.0, 'train_f1': 0.0,
                'test_accuracy': 0.0, 'test_precision': 0.0, 'test_recall': 0.0, 'test_f1': 0.0,
            }

    def _build_model(self, use_xgboost=None):
        """
        Construye el modelo base.
        [IMP-ML-009] Ahora usa XGBoost por defecto si está disponible.
        XGBoost maneja mejor los datos tabulares desbalanceados y valores nulos.
        """
        # Auto-detección: usar XGBoost si está disponible y no se especifica lo contrario
        if use_xgboost is None:
            use_xgboost = XGB_AVAILABLE

        depth = 6  # Aumentamos ligeramente para XGBoost
        est = 100
        min_leaf = 20

        if use_xgboost and XGB_AVAILABLE:
            logger.info("   🚀 Usando XGBoost (mejor manejo de datos desbalanceados)")
            # [IMP-ML-010] Configuración optimizada para lotería
            xgb = XGBClassifier(
                n_estimators=est,
                max_depth=depth,
                learning_rate=0.1,
                min_child_weight=min_leaf,
                subsample=0.8,
                colsample_bytree=0.8,
                # [IMP-ML-011] Métrica personalizada: usamos logloss que penaliza
                # menos las predicciones "cercanas" vs accuracy binaria
                objective='binary:logistic',
                eval_metric='logloss',
                use_label_encoder=False,
                n_jobs=-1,
                random_state=42,
                verbosity=0
            )
            return MultiOutputClassifier(xgb)
        else:
            if use_xgboost and not XGB_AVAILABLE:
                logger.warning("   ⚠️ XGBoost solicitado pero no disponible. Usando RandomForest.")
            rf = RandomForestClassifier(
                n_estimators=est,
                max_depth=depth - 1,  # RF necesita menos profundidad
                min_samples_leaf=min_leaf,
                max_features='sqrt',
                class_weight='balanced' if (self.version == "v3" and self.config['type'] == 'SET') else None,
                n_jobs=-1,
                random_state=42
            )
            return MultiOutputClassifier(rf)

    def _entrenar_manual(self, X_train, y_train):
        """Configuración manual de fallback (la antigua lógica)"""
        # Hiperparámetros conservadores para lotería (evitar overfitting)
        # [IMP-ML-001] Ajuste agresivo para reducir varianza
        
        logger.info(f"   Hiperparámetros Manuales: Depth=5, Est=100, MinLeaf=20")

        self.model = self._build_model()
        self.model.fit(X_train, y_train)

    # --- INFERENCIA Y AUTO-CURACIÓN ---

    def predecir(self, fecha_objetivo=None, estocastico=True, _intento_recuperacion=False):
        if self.model is None:
            self.entrenar()

        if self.model is None: return []

        # [IMP-RACHA-001] RACHA usa estrategia especial de Clasificación Binaria
        if self.game_id == "RACHA" and getattr(self, '_racha_binary_mode', False):
            df = pd.read_csv(self.maestro_file)
            return self._predecir_racha_binario(df)

        # Carga fresca para el input más reciente
        df = pd.read_csv(self.maestro_file).sort_values('sorteo', ascending=True)
        n_balls = self.config['n_balls']
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        
        # Fallback de columnas
        if len(input_cols) < n_balls:
            input_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
        
        df_valid = df.dropna(subset=input_cols)
        X_raw = df_valid[input_cols].values
        
        # ERR-006: Validación de tamaño de ventana para evitar IndexError
        if len(X_raw) < self.window_size:
            logger.warning(f"Ventana insuficiente para {self.game_id} ({len(X_raw)} < {self.window_size}). Retornando predicción vacía.")
            return []

        # Construcción del vector de predicción (últimos sorteos + fecha objetivo)
        input_features = []
        last_idx = len(X_raw)
        
        # El loop original asumía implícitamente que last_idx >= window_size
        # Ahora está protegido por el if anterior.
        for w in range(self.window_size):
            input_features.extend(X_raw[last_idx - self.window_size + w])
            
        # Determinar día objetivo
        if fecha_objetivo and hasattr(fecha_objetivo, 'weekday'):
            target_dow = fecha_objetivo.weekday()
        else:
            target_dow = datetime.now().weekday()

        input_features.append(target_dow)

        # [IMP-FEAT-001] Inyección de Rachas en Inferencia
        # Calculamos el mapa de calor usando toda la historia disponible hasta hoy
        current_heat_map = self._calcular_mapa_calor(X_raw, len(X_raw), lookback=10)
        input_features.extend(current_heat_map)

        # [IMP-FEAT-004] Vector de Gaps (Recencia) - EL ESLABÓN PERDIDO
        current_gaps = self._calcular_gaps(X_raw, len(X_raw))
        input_features.extend(current_gaps)

        # [IMP-FEAT-006] Deltas Promedio (Velocidad)
        current_deltas = self._calcular_deltas_promedio(X_raw, len(X_raw), lookback=3)
        input_features.extend(current_deltas)

        # [IMP-FEAT-007] Meta-Features del Biométrico
        current_meta = self._calcular_meta_features(X_raw, len(X_raw), lookback=5)
        input_features.extend(current_meta)

        X_pred = np.array([input_features])
        
        # --- FIX: Alineación de Features (Self-Healing de Dimensión) ---
        if hasattr(self.model, 'n_features_in_'):
            expected = self.model.n_features_in_
            current = X_pred.shape[1]
            if current != expected:
                logger.warning(f"⚠️ Mismatch de features: Modelo espera {expected}, input tiene {current}.")
                if current > expected:
                    # Asumimos que los features extra están al final (ej: heat map nuevo)
                    logger.info(f"✂️ Recortando input para coincidir con el modelo ({expected} cols).")
                    X_pred = X_pred[:, :expected]
                else:
                    logger.error("❌ Faltan features. Se requiere re-entrenamiento forzoso.")
                    # Disparamos error para que el catch de abajo inicie la recuperación
                    raise ValueError(f"Feature mismatch: expected {expected}, got {current}")
        
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, message=".*valid feature names.*")
                
                if self.version == "v4":
                    # v4: Predicción de bloque físico con limpieza de colisiones
                    raw_pred = self.model.predict(X_pred)[0]
                    numeros_unicos = []
                    for n in [int(x) for x in raw_pred]:
                        if n not in numeros_unicos and self.config['min_val'] <= n <= self.config['max']:
                            numeros_unicos.append(n)
                    
                    # Si hubo colisiones (números repetidos), rellenamos con los más probables
                    if len(numeros_unicos) < n_balls:
                        probs = self.model.predict_proba(X_pred)
                        # Sacamos los mejores candidatos que no estén ya en la lista
                        fallback = self._decode_one_hot_probs(probs, n_balls * 2)
                        for f in fallback:
                            if f not in numeros_unicos:
                                numeros_unicos.append(f)
                            if len(numeros_unicos) == n_balls: break
                    
                    return sorted(numeros_unicos[:n_balls])
                
                elif self.config['type'] == 'SET':
                    # v3: Inferencia probabilística estándar
                    probs = self.model.predict_proba(X_pred)
                    if estocastico:
                        return self._muestreo_probabilistico(probs, n_balls)
                    return self._decode_one_hot_probs(probs, n_balls)
                else:
                    # Caso Loto3 (Posicional)
                    prediction = self.model.predict(X_pred)
                    return [int(x) for x in prediction[0]]
                
        except Exception as e:
            # --- ZONA DE AUTO-CURACIÓN ---
            err_msg = str(e).lower()
            if not _intento_recuperacion and ("monotonic" in err_msg or "attribute" in err_msg or "version" in err_msg):
                print(f"♻️ Incompatibilidad de versión detectada. Re-entrenando...")
                self.model = None
                self.entrenar()
                return self.predecir(fecha_objetivo, estocastico, _intento_recuperacion=True)
            else:
                print(f"❌ Error crítico en predicción {self.game_id}: {e}")
                return []

# --- TEST UNITARIO INTERNO ---
if __name__ == "__main__":
    for g in ["LOTO", "LOTO3", "RACHA", "LOTO4"]:
        print(f"\n" + "="*30)
        print(f"TESTING UNIVERSE: {g}")
        for v in ["v3", "v4"]:
            oracle = OraculoNeural(g, version=v)
            res = oracle.predecir()
            print(f"   [{v}] Result: {res}")