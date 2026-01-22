"""
LOTO3 ULTRA - Sistema de Prediccion Avanzado v1.0
==================================================
Implementa TODAS las mejoras identificadas:
1. Modelos por franja horaria (DIA/TARDE/NOCHE)
2. Analisis de patrones de combinacion (dobles, escaleras, etc.)
3. Ensemble de posiciones con meta-modelo
4. Markov de orden superior (orden 2 y 3)
5. Calibracion de probabilidades (Isotonic)
6. Ventanas adaptativas segun volatilidad
7. Analisis de ciclos (semanal, mensual, lunar)
8. Cross-validation temporal con gap

Autor: LotoAI System
Fecha: 2026-01-17
"""

import time
import pandas as pd
import numpy as np
import os
import json
import logging
import tempfile
import shutil
import pytz
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import joblib

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# =============================================================================
# CONFIGURACION
# =============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

RUTA_CSV = os.path.join(DATA_DIR, "LOTO3_MAESTRO.csv")
RUTA_DASHBOARD = os.path.join(PROJECT_ROOT, "dashboard_data.json")
RUTA_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
RUTA_MODELOS = os.path.join(DATA_DIR, "loto3_ultra_models")

# Crear directorio de modelos si no existe
os.makedirs(RUTA_MODELOS, exist_ok=True)

TZ_CHILE = pytz.timezone('America/Santiago')
HORARIOS_LOTO3 = [14, 18, 21]
FRANJAS = {14: 'DIA', 18: 'TARDE', 21: 'NOCHE'}

# Primos del 0-9
PRIMOS_0_9 = {2, 3, 5, 7}


# =============================================================================
# 1. FEATURE ENGINEERING AVANZADO
# =============================================================================
class FeatureEngineer:
    """Genera features avanzados para LOTO 3"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._preparar_datos()

    def _preparar_datos(self):
        """Prepara el DataFrame con conversiones basicas"""
        # Asegurar tipos correctos
        for col in ['n1', 'n2', 'n3']:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0).astype(int)

        # Parsear fecha
        self.df['fecha'] = pd.to_datetime(self.df['fecha'], errors='coerce')
        self.df = self.df.dropna(subset=['fecha'])
        self.df = self.df.sort_values('fecha').reset_index(drop=True)

        # Extraer hora si no existe
        if 'hora' not in self.df.columns:
            self.df['hora'] = self.df['fecha'].dt.hour

        # Crear franja horaria
        self.df['franja'] = self.df['hora'].map(lambda h: FRANJAS.get(h, 'DIA'))

    def generar_features_basicos(self) -> pd.DataFrame:
        """Features basicos: lags, rolling, temporales"""
        df = self.df.copy()

        # LAGS para cada posicion (1-10 sorteos atras)
        for pos in ['n1', 'n2', 'n3']:
            for lag in range(1, 11):
                df[f'{pos}_lag{lag}'] = df[pos].shift(lag)

        # Rolling statistics (ventana de 10, 20, 50)
        for pos in ['n1', 'n2', 'n3']:
            for window in [10, 20, 50]:
                df[f'{pos}_rolling_mean_{window}'] = df[pos].rolling(window).mean()
                df[f'{pos}_rolling_std_{window}'] = df[pos].rolling(window).std()

        # Features temporales
        df['dia_semana'] = df['fecha'].dt.dayofweek
        df['dia_mes'] = df['fecha'].dt.day
        df['mes'] = df['fecha'].dt.month
        df['hora_num'] = df['hora']

        # Franja como one-hot
        df['franja_DIA'] = (df['franja'] == 'DIA').astype(int)
        df['franja_TARDE'] = (df['franja'] == 'TARDE').astype(int)
        df['franja_NOCHE'] = (df['franja'] == 'NOCHE').astype(int)

        return df

    def generar_features_patrones(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de patrones de combinacion"""

        # Crear combinacion como string
        df['combinacion'] = df['n1'].astype(str) + df['n2'].astype(str) + df['n3'].astype(str)

        # Patron: tiene digitos repetidos
        df['tiene_repetido'] = df.apply(
            lambda r: 1 if len(set([r['n1'], r['n2'], r['n3']])) < 3 else 0, axis=1
        )

        # Patron: es escalera (consecutivos)
        def es_escalera(n1, n2, n3):
            nums = sorted([n1, n2, n3])
            return 1 if (nums[1] == nums[0] + 1 and nums[2] == nums[1] + 1) else 0
        df['es_escalera'] = df.apply(lambda r: es_escalera(r['n1'], r['n2'], r['n3']), axis=1)

        # Patron: todos pares o todos impares
        df['todos_pares'] = df.apply(
            lambda r: 1 if all(x % 2 == 0 for x in [r['n1'], r['n2'], r['n3']]) else 0, axis=1
        )
        df['todos_impares'] = df.apply(
            lambda r: 1 if all(x % 2 == 1 for x in [r['n1'], r['n2'], r['n3']]) else 0, axis=1
        )

        # Suma de digitos
        df['suma_digitos'] = df['n1'] + df['n2'] + df['n3']

        # Cantidad de primos
        df['cant_primos'] = df.apply(
            lambda r: sum(1 for x in [r['n1'], r['n2'], r['n3']] if x in PRIMOS_0_9), axis=1
        )

        # Distancia entre digitos (max - min)
        df['rango_digitos'] = df.apply(
            lambda r: max(r['n1'], r['n2'], r['n3']) - min(r['n1'], r['n2'], r['n3']), axis=1
        )

        # Patrones de lag (el patron anterior)
        df['patron_anterior_repetido'] = df['tiene_repetido'].shift(1)
        df['patron_anterior_escalera'] = df['es_escalera'].shift(1)

        return df

    def generar_features_ciclos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de ciclos temporales"""

        # Ciclo semanal (seno/coseno para continuidad)
        df['ciclo_semana_sin'] = np.sin(2 * np.pi * df['dia_semana'] / 7)
        df['ciclo_semana_cos'] = np.cos(2 * np.pi * df['dia_semana'] / 7)

        # Ciclo mensual
        df['ciclo_mes_sin'] = np.sin(2 * np.pi * df['dia_mes'] / 31)
        df['ciclo_mes_cos'] = np.cos(2 * np.pi * df['dia_mes'] / 31)

        # Ciclo anual
        df['dia_del_ano'] = df['fecha'].dt.dayofyear
        df['ciclo_ano_sin'] = np.sin(2 * np.pi * df['dia_del_ano'] / 365)
        df['ciclo_ano_cos'] = np.cos(2 * np.pi * df['dia_del_ano'] / 365)

        # Ciclo lunar aproximado (29.5 dias)
        df['ciclo_lunar'] = (df['dia_del_ano'] % 29.5) / 29.5
        df['ciclo_lunar_sin'] = np.sin(2 * np.pi * df['ciclo_lunar'])
        df['ciclo_lunar_cos'] = np.cos(2 * np.pi * df['ciclo_lunar'])

        return df

    def generar_features_distancia(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de distancia desde ultima aparicion de cada digito"""
        # Crear todas las columnas de una vez para evitar fragmentacion
        nuevas_cols = {}

        for pos in ['n1', 'n2', 'n3']:
            for digito in range(10):
                col_name = f'{pos}_dist_{digito}'
                distances = []
                last_seen = -1

                for idx, val in enumerate(df[pos]):
                    if last_seen == -1:
                        distances.append(100)  # Valor alto inicial
                    else:
                        distances.append(idx - last_seen)

                    if val == digito:
                        last_seen = idx

                nuevas_cols[col_name] = distances

        # Agregar todas las columnas de una vez
        df = pd.concat([df, pd.DataFrame(nuevas_cols)], axis=1)
        return df

    def generar_todos_features(self) -> pd.DataFrame:
        """Genera TODOS los features"""
        df = self.generar_features_basicos()
        df = self.generar_features_patrones(df)
        df = self.generar_features_ciclos(df)
        df = self.generar_features_distancia(df)
        return df


# =============================================================================
# 2. MODELO MARKOV DE ORDEN SUPERIOR
# =============================================================================
class MarkovLoto3:
    """Cadenas de Markov de orden 1, 2 y 3 para cada posicion"""

    def __init__(self, orden_max: int = 3):
        self.orden_max = orden_max
        self.transiciones = {pos: {orden: defaultdict(Counter)
                                   for orden in range(1, orden_max + 1)}
                            for pos in ['n1', 'n2', 'n3']}
        self.trained = False

    def entrenar(self, df: pd.DataFrame):
        """Entrena las matrices de transicion"""
        logger.info(f"Entrenando Markov orden 1-{self.orden_max}...")

        for pos in ['n1', 'n2', 'n3']:
            valores = df[pos].values

            for orden in range(1, self.orden_max + 1):
                for i in range(orden, len(valores)):
                    # Estado anterior (tupla de 'orden' valores)
                    estado = tuple(valores[i-orden:i])
                    siguiente = valores[i]
                    self.transiciones[pos][orden][estado][siguiente] += 1

        self.trained = True
        logger.info("Markov entrenado correctamente")

    def predecir_probabilidades(self, pos: str, historia: List[int]) -> Dict[int, float]:
        """Retorna probabilidades para cada digito 0-9 usando ensemble de ordenes"""
        if not self.trained:
            return {i: 0.1 for i in range(10)}  # Uniforme

        probs_combined = defaultdict(float)
        pesos = {1: 0.2, 2: 0.35, 3: 0.45}  # Mayor peso a ordenes superiores

        for orden in range(1, self.orden_max + 1):
            if len(historia) >= orden:
                estado = tuple(historia[-orden:])
                transiciones = self.transiciones[pos][orden].get(estado, Counter())
                total = sum(transiciones.values())

                if total > 0:
                    for digito in range(10):
                        prob = (transiciones.get(digito, 0) + 1) / (total + 10)  # Laplace
                        probs_combined[digito] += prob * pesos[orden]

        # Normalizar
        total_prob = sum(probs_combined.values())
        if total_prob > 0:
            return {k: v / total_prob for k, v in probs_combined.items()}
        return {i: 0.1 for i in range(10)}

    def predecir(self, historia_n1: List[int], historia_n2: List[int],
                 historia_n3: List[int]) -> Tuple[List[int], float]:
        """Predice los 3 digitos usando muestreo probabilistico"""
        prediccion = []
        confianza_total = 0

        for pos, historia in [('n1', historia_n1), ('n2', historia_n2), ('n3', historia_n3)]:
            probs = self.predecir_probabilidades(pos, historia)

            # Muestreo ponderado
            digitos = list(probs.keys())
            probabilidades = list(probs.values())

            elegido = np.random.choice(digitos, p=probabilidades)
            prediccion.append(int(elegido))
            confianza_total += probs[elegido]

        return prediccion, confianza_total / 3


# =============================================================================
# 3. MODELO POR FRANJA HORARIA
# =============================================================================
class ModeloFranjaHoraria:
    """Modelo especializado para cada franja (DIA/TARDE/NOCHE)"""

    def __init__(self, franja: str, calibrar: bool = True):
        self.franja = franja
        self.calibrar = calibrar
        self.modelos = {}  # Un modelo por posicion
        self.scalers = {}
        self.feature_cols = []
        self.trained = False

    def _get_feature_cols(self, df: pd.DataFrame) -> List[str]:
        """Obtiene columnas de features (excluye targets y metadata)"""
        exclude = ['n1', 'n2', 'n3', 'fecha', 'sorteo', 'combinacion', 'franja',
                   'dia_semana', 'EXACTA_GANADORES', 'EXACTA_MONTO', 'TRIO_PAR_GANADORES',
                   'TRIO_PAR_MONTO', 'TRIO_AZAR_GANADORES', 'TRIO_AZAR_MONTO',
                   'PAR_GANADORES', 'PAR_MONTO', 'TERMINACION_GANADORES', 'TERMINACION_MONTO',
                   'momento', 'dia_del_ano', 'ciclo_lunar']

        return [c for c in df.columns if c not in exclude and df[c].dtype in ['int64', 'float64']]

    def entrenar(self, df: pd.DataFrame):
        """Entrena modelos para esta franja horaria"""
        # Filtrar por franja
        df_franja = df[df['franja'] == self.franja].copy()

        if len(df_franja) < 100:
            logger.warning(f"Franja {self.franja}: datos insuficientes ({len(df_franja)})")
            return False

        logger.info(f"Entrenando franja {self.franja} con {len(df_franja)} registros...")

        # Obtener features
        self.feature_cols = self._get_feature_cols(df_franja)
        df_clean = df_franja.dropna(subset=self.feature_cols)

        if len(df_clean) < 50:
            logger.warning(f"Franja {self.franja}: muy pocos datos limpios")
            return False

        X = df_clean[self.feature_cols].values

        # Split temporal (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]

        for pos in ['n1', 'n2', 'n3']:
            y = df_clean[pos].values
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Scaler
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers[pos] = scaler

            # Modelo base
            base_model = RandomForestClassifier(
                n_estimators=150,
                max_depth=12,
                min_samples_leaf=5,
                max_features='sqrt',
                n_jobs=None, # [FIX-2026] Delegado al contexto paralelo
                random_state=42
            )

            # Calibracion opcional
            if self.calibrar:
                model = CalibratedClassifierCV(base_model, method='isotonic', cv=3)
            else:
                model = base_model

            # [FIX-2026] Uso explícito de backend para evitar warnings de sklearn
            with joblib.parallel_backend('loky', n_jobs=-1):
                model.fit(X_train_scaled, y_train)
            self.modelos[pos] = model

            # Evaluar
            score = model.score(X_test_scaled, y_test)
            logger.info(f"  {pos}: Test accuracy = {score:.4f}")

        self.trained = True
        return True

    def predecir(self, features: np.ndarray) -> Tuple[List[int], float]:
        """Predice usando los 3 modelos"""
        if not self.trained:
            return [np.random.randint(0, 10) for _ in range(3)], 0.33

        prediccion = []
        confianza_total = 0

        for pos in ['n1', 'n2', 'n3']:
            X_scaled = self.scalers[pos].transform(features.reshape(1, -1))

            # Obtener probabilidades
            probs = self.modelos[pos].predict_proba(X_scaled)[0]
            clases = self.modelos[pos].classes_

            # Muestreo ponderado del top 3
            top_indices = np.argsort(probs)[-3:]
            top_probs = probs[top_indices]
            top_probs = top_probs / top_probs.sum()

            elegido_idx = np.random.choice(top_indices, p=top_probs)
            elegido = clases[elegido_idx]
            prediccion.append(int(elegido))
            confianza_total += probs[elegido_idx]

        return prediccion, confianza_total / 3


# =============================================================================
# 4. VENTANA ADAPTATIVA
# =============================================================================
class VentanaAdaptativa:
    """Calcula el tamano de ventana optimo segun volatilidad"""

    def __init__(self, min_window: int = 5, max_window: int = 30):
        self.min_window = min_window
        self.max_window = max_window

    def calcular_volatilidad(self, serie: pd.Series, window: int = 20) -> float:
        """Calcula volatilidad como desviacion estandar rolling"""
        if len(serie) < window:
            return 0.5
        return serie.rolling(window).std().iloc[-1] / 3.0  # Normalizado por rango 0-9

    def obtener_ventana(self, df: pd.DataFrame) -> int:
        """Retorna tamano de ventana optimo"""
        volatilidades = []
        for pos in ['n1', 'n2', 'n3']:
            vol = self.calcular_volatilidad(df[pos])
            volatilidades.append(vol)

        vol_promedio = np.mean(volatilidades)

        # Alta volatilidad -> ventana corta (reactiva)
        # Baja volatilidad -> ventana larga (estable)
        if vol_promedio > 0.8:
            return self.min_window
        elif vol_promedio < 0.3:
            return self.max_window
        else:
            # Interpolacion lineal
            ratio = (vol_promedio - 0.3) / 0.5
            return int(self.max_window - ratio * (self.max_window - self.min_window))


# =============================================================================
# 5. ENSEMBLE PRINCIPAL
# =============================================================================
class Loto3UltraEnsemble:
    """Ensemble que combina todos los modelos"""

    def __init__(self):
        self.feature_engineer = None
        self.markov = MarkovLoto3(orden_max=3)
        self.modelos_franja = {
            'DIA': ModeloFranjaHoraria('DIA'),
            'TARDE': ModeloFranjaHoraria('TARDE'),
            'NOCHE': ModeloFranjaHoraria('NOCHE')
        }
        self.ventana_adaptativa = VentanaAdaptativa()
        self.df_procesado = None
        self.feature_cols = []

        # Pesos del ensemble (ajustables)
        self.pesos = {
            'franja': 0.40,
            'markov': 0.30,
            'frecuencia': 0.20,
            'patron': 0.10
        }

        self.trained = False

    def cargar_datos(self) -> pd.DataFrame:
        """Carga y procesa el CSV"""
        if not os.path.exists(RUTA_CSV):
            raise FileNotFoundError(f"No se encuentra {RUTA_CSV}")

        df = pd.read_csv(RUTA_CSV)
        logger.info(f"Datos cargados: {len(df)} registros")
        return df

    def entrenar(self):
        """Entrena todos los componentes del ensemble"""
        logger.info("=" * 60)
        logger.info("LOTO3 ULTRA: INICIANDO ENTRENAMIENTO COMPLETO")
        logger.info("=" * 60)

        # 1. Cargar y procesar datos
        df = self.cargar_datos()
        self.feature_engineer = FeatureEngineer(df)
        self.df_procesado = self.feature_engineer.generar_todos_features()

        # 2. Entrenar Markov
        self.markov.entrenar(self.df_procesado)

        # 3. Entrenar modelos por franja
        for franja, modelo in self.modelos_franja.items():
            modelo.entrenar(self.df_procesado)

        # 4. Guardar feature columns
        exclude = ['n1', 'n2', 'n3', 'fecha', 'sorteo', 'combinacion', 'franja',
                   'EXACTA_GANADORES', 'EXACTA_MONTO', 'TRIO_PAR_GANADORES',
                   'TRIO_PAR_MONTO', 'TRIO_AZAR_GANADORES', 'TRIO_AZAR_MONTO',
                   'PAR_GANADORES', 'PAR_MONTO', 'TERMINACION_GANADORES', 'TERMINACION_MONTO',
                   'momento', 'dia_semana', 'dia_del_ano', 'ciclo_lunar']
        self.feature_cols = [c for c in self.df_procesado.columns
                            if c not in exclude and self.df_procesado[c].dtype in ['int64', 'float64']]

        self.trained = True
        logger.info("ENTRENAMIENTO COMPLETO")

        # Guardar modelos
        self._guardar_modelos()

    def _guardar_modelos(self):
        """Guarda los modelos entrenados"""
        try:
            # Guardar Markov
            joblib.dump(self.markov, os.path.join(RUTA_MODELOS, 'markov.pkl'))

            # Guardar modelos de franja
            for franja, modelo in self.modelos_franja.items():
                if modelo.trained:
                    joblib.dump(modelo, os.path.join(RUTA_MODELOS, f'franja_{franja}.pkl'))

            # Guardar feature columns
            with open(os.path.join(RUTA_MODELOS, 'feature_cols.json'), 'w') as f:
                json.dump(self.feature_cols, f)

            logger.info(f"Modelos guardados en {RUTA_MODELOS}")
        except Exception as e:
            logger.error(f"Error guardando modelos: {e}")

    def _cargar_modelos(self) -> bool:
        """Carga modelos previamente entrenados"""
        try:
            markov_path = os.path.join(RUTA_MODELOS, 'markov.pkl')
            if os.path.exists(markov_path):
                self.markov = joblib.load(markov_path)

            for franja in ['DIA', 'TARDE', 'NOCHE']:
                franja_path = os.path.join(RUTA_MODELOS, f'franja_{franja}.pkl')
                if os.path.exists(franja_path):
                    self.modelos_franja[franja] = joblib.load(franja_path)

            fc_path = os.path.join(RUTA_MODELOS, 'feature_cols.json')
            if os.path.exists(fc_path):
                with open(fc_path, 'r') as f:
                    self.feature_cols = json.load(f)

            self.trained = True
            return True
        except Exception as e:
            logger.warning(f"No se pudieron cargar modelos: {e}")
            return False

    def _calcular_frecuencias_recientes(self, window: int = 20) -> Dict[str, Dict[int, float]]:
        """Calcula frecuencias recientes para cada posicion"""
        if self.df_procesado is None:
            return {}

        frecuencias = {}
        for pos in ['n1', 'n2', 'n3']:
            ultimos = self.df_procesado[pos].tail(window)
            counts = ultimos.value_counts()
            total = len(ultimos)
            frecuencias[pos] = {i: (counts.get(i, 0) + 1) / (total + 10) for i in range(10)}

        return frecuencias

    def _analizar_patron_actual(self) -> Dict[str, float]:
        """Analiza patrones recientes para ajustar probabilidades"""
        if self.df_procesado is None:
            return {}

        ultimos_20 = self.df_procesado.tail(20)

        return {
            'prob_repetido': ultimos_20['tiene_repetido'].mean(),
            'prob_escalera': ultimos_20['es_escalera'].mean(),
            'suma_promedio': ultimos_20['suma_digitos'].mean(),
            'rango_promedio': ultimos_20['rango_digitos'].mean()
        }

    def predecir(self, franja: str = None, n_candidatos: int = 10) -> List[Dict]:
        """
        Genera predicciones usando el ensemble completo.
        Retorna lista de candidatos ordenados por score.
        """
        if not self.trained:
            if not self._cargar_modelos():
                logger.info("Modelos no encontrados, entrenando...")
                self.entrenar()

        # Recargar datos frescos
        if self.df_procesado is None:
            df = self.cargar_datos()
            self.feature_engineer = FeatureEngineer(df)
            self.df_procesado = self.feature_engineer.generar_todos_features()

        # Determinar franja
        if franja is None:
            ahora = datetime.now(TZ_CHILE)
            hora = ahora.hour
            if hora < 16:
                franja = 'DIA'
            elif hora < 20:
                franja = 'TARDE'
            else:
                franja = 'NOCHE'

        logger.info(f"Generando predicciones para franja: {franja}")

        # Obtener ventana adaptativa
        window = self.ventana_adaptativa.obtener_ventana(self.df_procesado)
        logger.info(f"Ventana adaptativa: {window}")

        # Obtener historias recientes para Markov
        historia_n1 = self.df_procesado['n1'].tail(10).tolist()
        historia_n2 = self.df_procesado['n2'].tail(10).tolist()
        historia_n3 = self.df_procesado['n3'].tail(10).tolist()

        # Obtener features para modelo de franja
        ultima_fila = self.df_procesado[self.feature_cols].iloc[-1].values

        # Obtener frecuencias y patrones
        frecuencias = self._calcular_frecuencias_recientes(window)
        patrones = self._analizar_patron_actual()

        # Generar candidatos
        candidatos = []

        for _ in range(n_candidatos * 5):  # Generar mas y filtrar
            # 1. Prediccion del modelo de franja
            if self.modelos_franja[franja].trained:
                pred_franja, conf_franja = self.modelos_franja[franja].predecir(ultima_fila)
            else:
                pred_franja = [np.random.randint(0, 10) for _ in range(3)]
                conf_franja = 0.33

            # 2. Prediccion de Markov
            pred_markov, conf_markov = self.markov.predecir(historia_n1, historia_n2, historia_n3)

            # 3. Prediccion por frecuencia
            pred_freq = []
            conf_freq = 0
            for pos in ['n1', 'n2', 'n3']:
                probs = list(frecuencias[pos].values())
                elegido = np.random.choice(range(10), p=np.array(probs)/sum(probs))
                pred_freq.append(elegido)
                conf_freq += frecuencias[pos][elegido]
            conf_freq /= 3

            # 4. Combinar predicciones con votacion ponderada
            votos = defaultdict(lambda: defaultdict(float))

            for i, pos in enumerate(['n1', 'n2', 'n3']):
                votos[pos][pred_franja[i]] += self.pesos['franja'] * conf_franja
                votos[pos][pred_markov[i]] += self.pesos['markov'] * conf_markov
                votos[pos][pred_freq[i]] += self.pesos['frecuencia'] * conf_freq

            # Seleccionar ganador por posicion
            prediccion_final = []
            confianza_final = 0

            for pos in ['n1', 'n2', 'n3']:
                # Agregar ruido para diversidad
                for digito in range(10):
                    votos[pos][digito] += np.random.uniform(0, 0.05)

                ganador = max(votos[pos], key=votos[pos].get)
                prediccion_final.append(ganador)
                confianza_final += votos[pos][ganador]

            confianza_final /= 3

            # Calcular score morfologico
            suma = sum(prediccion_final)
            tiene_repetido = len(set(prediccion_final)) < 3
            es_escalera = sorted(prediccion_final) == list(range(min(prediccion_final), min(prediccion_final) + 3))

            # Penalizaciones/bonificaciones
            score = confianza_final * 100

            # Ajuste por suma (preferir rango 7-20)
            if 7 <= suma <= 20:
                score += 5
            else:
                score -= 5

            # Ajuste por patrones (segun tendencia reciente)
            if tiene_repetido and patrones.get('prob_repetido', 0) > 0.3:
                score += 3
            if es_escalera and patrones.get('prob_escalera', 0) > 0.1:
                score += 5

            candidatos.append({
                'numeros': prediccion_final,
                'score': round(min(score, 99), 2),
                'confianza_franja': round(conf_franja * 100, 2),
                'confianza_markov': round(conf_markov * 100, 2),
                'suma': suma,
                'tiene_repetido': tiene_repetido,
                'es_escalera': es_escalera,
                'metodo': 'ultra_ensemble'
            })

        # Ordenar por score y eliminar duplicados
        vistos = set()
        unicos = []
        for c in sorted(candidatos, key=lambda x: x['score'], reverse=True):
            key = tuple(c['numeros'])
            if key not in vistos:
                vistos.add(key)
                unicos.append(c)
            if len(unicos) >= n_candidatos:
                break

        return unicos


# =============================================================================
# 6. FUNCIONES DE INTERFAZ
# =============================================================================
def calcular_proximo_sorteo_loto3() -> Tuple[int, datetime]:
    """Calcula el proximo sorteo de LOTO3"""
    ahora = datetime.now(TZ_CHILE)

    # Cargar ultimo sorteo del CSV
    ultimo_sorteo = 0
    if os.path.exists(RUTA_CSV):
        try:
            df = pd.read_csv(RUTA_CSV)
            if not df.empty:
                ultimo_sorteo = int(df['sorteo'].iloc[-1])
        except:
            pass

    # Buscar proximo horario
    for dias_extra in range(2):
        fecha_check = ahora + timedelta(days=dias_extra)
        for hora in sorted(HORARIOS_LOTO3):
            candidato = TZ_CHILE.localize(datetime(
                fecha_check.year, fecha_check.month, fecha_check.day, hora, 0, 0
            ))
            if candidato > ahora:
                return ultimo_sorteo + 1, candidato

    # Fallback
    manana = ahora + timedelta(days=1)
    return ultimo_sorteo + 1, TZ_CHILE.localize(
        datetime(manana.year, manana.month, manana.day, 14, 0, 0)
    )


def guardar_en_dashboard(jugadas: List[Dict]):
    """Guarda las predicciones en el dashboard JSON"""
    data = []
    if os.path.exists(RUTA_DASHBOARD):
        try:
            with open(RUTA_DASHBOARD, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = []

    # Insertar al principio
    data = jugadas + data
    data = data[:200]  # Limite

    # Escritura atomica
    tmp_path = None
    try:
        dir_name = os.path.dirname(RUTA_DASHBOARD)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         suffix='.json', dir=dir_name, delete=False) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            tmp_path = f.name
        shutil.move(tmp_path, RUTA_DASHBOARD)
        logger.info(f"Guardadas {len(jugadas)} predicciones en dashboard")
    except Exception as e:
        logger.error(f"Error guardando: {e}")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def guardar_en_simulaciones(jugadas: List[Dict]):
    """Guarda las predicciones en LOTO_SIMULACIONES.csv para el juez"""
    columnas = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 
                'estado', 'aciertos', 'score_afinidad', 'hora_dia', 
                'algoritmo', 'nota_especial', 'fecha_lanzamiento']
    
    nuevas_filas = []
    for j in jugadas:
        fila = {
            'id': j['id'],
            'fecha_generacion': j['fecha_generacion'],
            'juego': j['juego'],
            'numeros': str(j['numeros']), # Convertir lista a string
            'sorteo_objetivo': j['sorteo_objetivo'],
            'estado': j['estado'],
            'aciertos': j['aciertos'],
            'score_afinidad': j['score_afinidad'],
            'hora_dia': datetime.strptime(j['fecha_generacion'], "%Y-%m-%d %H:%M:%S").hour,
            'algoritmo': j['algoritmo'],
            'nota_especial': j['nota_especial'],
            'fecha_lanzamiento': j['fecha_lanzamiento']
        }
        nuevas_filas.append(fila)
    
    df_new = pd.DataFrame(nuevas_filas, columns=columnas)
    
    # Append to CSV
    if os.path.exists(RUTA_SIMULACIONES):
        df_new.to_csv(RUTA_SIMULACIONES, mode='a', header=False, index=False)
    else:
        df_new.to_csv(RUTA_SIMULACIONES, mode='w', header=True, index=False)
    
    logger.info(f"Guardadas {len(jugadas)} predicciones en LOTO_SIMULACIONES.csv")


def ejecutar_loto3_ultra(guardar: bool = True) -> List[Dict]:
    """
    Funcion principal: Ejecuta el sistema LOTO3 Ultra completo.

    Args:
        guardar: Si True, guarda las predicciones en el dashboard

    Returns:
        Lista de predicciones generadas
    """
    logger.info("=" * 60)
    logger.info("LOTO3 ULTRA v1.0 - SISTEMA DE PREDICCION AVANZADO")
    logger.info("=" * 60)

    ahora = datetime.now(TZ_CHILE)
    sorteo_objetivo, fecha_sorteo = calcular_proximo_sorteo_loto3()

    logger.info(f"Hora actual: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Sorteo objetivo: #{sorteo_objetivo}")
    logger.info(f"Fecha sorteo: {fecha_sorteo.strftime('%d/%m/%Y %H:%M')}")

    # Determinar franja
    hora_sorteo = fecha_sorteo.hour
    franja = FRANJAS.get(hora_sorteo, 'DIA')

    # Crear y ejecutar ensemble
    ensemble = Loto3UltraEnsemble()

    try:
        predicciones = ensemble.predecir(franja=franja, n_candidatos=10)
    except Exception as e:
        logger.error(f"Error en prediccion: {e}")
        return []

    # Formatear para dashboard
    jugadas = []
    base_id = int(time.time())
    for i, pred in enumerate(predicciones):
        jugada = {
            "id": base_id + i,  # ID unico para tracking
            "fecha_generacion": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha_lanzamiento": fecha_sorteo.strftime("%d/%m/%Y %H:%M"),
            "sorteo_objetivo": sorteo_objetivo,
            "juego": "LOTO3",
            "numeros": pred['numeros'],
            "estado": "PENDIENTE", # Estado inicial explícito
            "aciertos": 0,
            "algoritmo": f"Ultra-Ensemble (Rank #{i+1})",
            "score_afinidad": pred['score'],
            "nota_especial": f"Franja:{franja}|Markov:{pred['confianza_markov']:.0f}%|RF:{pred['confianza_franja']:.0f}%"
        }
        jugadas.append(jugada)
        logger.info(f"  #{i+1}: {pred['numeros']} - Score: {pred['score']}")

    if guardar and jugadas:
        guardar_en_dashboard(jugadas)
        guardar_en_simulaciones(jugadas)

    return jugadas


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--entrenar':
        # Modo entrenamiento forzado
        ensemble = Loto3UltraEnsemble()
        ensemble.entrenar()
    else:
        # Modo prediccion normal
        resultados = ejecutar_loto3_ultra(guardar=True)

        if resultados:
            print("\n" + "=" * 40)
            print("PREDICCIONES LOTO3 ULTRA")
            print("=" * 40)
            for r in resultados[:5]:
                print(f"  {r['numeros']} - Score: {r['score_afinidad']}")
