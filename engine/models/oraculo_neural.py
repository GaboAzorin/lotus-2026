import pandas as pd
import numpy as np
import os
import joblib
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import TimeSeriesSplit
from datetime import datetime
import logging

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
        if os.path.exists(self.model_file):
            try:
                self.model = joblib.load(self.model_file)
                # Validación de compatibilidad inmediata
                if hasattr(self.model, "estimators_"):
                    print(f"✅ Modelo {version} cargado exitosamente.")
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

        X, y, _, _ = self._preparar_dataset(df)
        if X is None: return

        samples = len(X)

        # --- AUDITORÍA v4: TRAIN/TEST SPLIT TEMPORAL ---
        # Usamos 80% para entrenamiento, 20% para validación
        # Split TEMPORAL (no aleatorio) para evitar data leakage
        split_idx = int(samples * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        logger.info(f"   Split temporal: Train={len(X_train)}, Test={len(X_test)}")

        # Hiperparámetros conservadores para lotería (evitar overfitting)
        depth = 8  # Reducido de 10 para más regularización
        est = 80   # Reducido de 100
        min_leaf = 10  # Aumentado de 5 para más generalización

        logger.info(f"   Hiperparámetros: Depth={depth}, Est={est}, MinLeaf={min_leaf}")

        # Configuración del Bosque con regularización
        rf = RandomForestClassifier(
            n_estimators=est,
            max_depth=depth,
            min_samples_leaf=min_leaf,
            max_features='sqrt',  # Reducir features por árbol
            class_weight='balanced' if (self.version == "v3" and self.config['type'] == 'SET') else None,
            n_jobs=-1,
            random_state=42
        )

        self.model = MultiOutputClassifier(rf)
        self.model.fit(X_train, y_train)

        # --- MÉTRICAS DE EVALUACIÓN REALISTAS ---
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        # Alerta si hay overfitting severo (para lotería, train > 0.5 ya es sospechoso)
        if train_score > 0.5 and test_score < 0.15:
            logger.warning(f"   ALERTA CRÍTICA: Overfitting severo detectado - Train: {train_score:.3f}, Test: {test_score:.3f}. El modelo puede estar memorizando ruido.")
        else:
            logger.info(f"   Métricas - Train: {train_score:.3f}, Test: {test_score:.3f}")

        # Para lotería, esperamos accuracy muy baja (<10% es realista)
        if test_score > 0.3:
            logger.warning(f"   SOSPECHA: Test accuracy demasiado alta ({test_score:.3f}). Revisar data leakage.")

        # Guardado con alta compresión
        joblib.dump(self.model, self.model_file, compress=9)
        logger.info(f"Modelo {self.version} guardado en {os.path.basename(self.model_file)}")

        return {'train_score': train_score, 'test_score': test_score}

    # --- INFERENCIA Y AUTO-CURACIÓN ---

    def predecir(self, fecha_objetivo=None, estocastico=True, _intento_recuperacion=False):
        if self.model is None: 
            self.entrenar()
        
        if self.model is None: return []

        # Carga fresca para el input más reciente
        df = pd.read_csv(self.maestro_file).sort_values('sorteo', ascending=True)
        n_balls = self.config['n_balls']
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        
        # Fallback de columnas
        if len(input_cols) < n_balls:
            input_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
        
        df_valid = df.dropna(subset=input_cols)
        X_raw = df_valid[input_cols].values
        
        if len(X_raw) < self.window_size:
            print(f"⚠️ Ventana insuficiente ({len(X_raw)} < {self.window_size})")
            return []

        # Construcción del vector de predicción (últimos sorteos + fecha objetivo)
        input_features = []
        last_idx = len(X_raw)
        for w in range(self.window_size):
            input_features.extend(X_raw[last_idx - self.window_size + w])
            
        # Determinar día objetivo
        if fecha_objetivo and hasattr(fecha_objetivo, 'weekday'):
            target_dow = fecha_objetivo.weekday()
        else:
            target_dow = datetime.now().weekday()

        input_features.append(target_dow)
        X_pred = np.array([input_features])
        
        try:
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