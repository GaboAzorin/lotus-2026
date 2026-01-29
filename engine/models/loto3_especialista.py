"""
LOTO3 ESPECIALISTA - Modelos Especializados para PAR y TERMINACION
===================================================================
Sistema de prediccion enfocado en maximizar aciertos en las modalidades
de menor premio pero mayor probabilidad relativa:

- PAR (20x): Predice pares inicial (n1n2) y final (n2n3)
- TERMINACION (4x): Predice el ultimo digito (n3)

Arquitectura:
- MarkovPares: Cadenas de Markov especializadas en pares (00-99)
- MarkovTerminacion: Modelos por franja horaria para n3
- Loto3Especialista: Ensemble que combina Markov + RF + Frecuencia

Autor: LotoAI System
Fecha: 2026-01-29
"""

import os
import sys
import json
import time
import logging
import tempfile
import shutil
import pytz
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional

from sklearn.ensemble import RandomForestClassifier
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
RUTA_MODELOS = os.path.join(DATA_DIR, "loto3_especialista_models")

# Crear directorio de modelos si no existe
os.makedirs(RUTA_MODELOS, exist_ok=True)

TZ_CHILE = pytz.timezone('America/Santiago')
HORARIOS_LOTO3 = [14, 18, 21]
FRANJAS = {14: 'DIA', 18: 'TARDE', 21: 'NOCHE'}


# =============================================================================
# 1. MARKOV PARES - Especializado en pares 00-99
# =============================================================================
class MarkovPares:
    """
    Cadenas de Markov especializadas en pares completos (00-99).

    Estados: 100 clases (pares del 00 al 99)
    Ordenes: 1-3 con pesos: O1=20%, O2=35%, O3=45%
    Modelos separados para:
    - par_inicial: n1n2 (primeros dos digitos)
    - par_final: n2n3 (ultimos dos digitos)
    """

    def __init__(self, orden_max: int = 3):
        self.orden_max = orden_max
        # Transiciones separadas para par_inicial y par_final
        self.transiciones_inicial = {
            orden: defaultdict(Counter) for orden in range(1, orden_max + 1)
        }
        self.transiciones_final = {
            orden: defaultdict(Counter) for orden in range(1, orden_max + 1)
        }
        self.pesos_orden = {1: 0.20, 2: 0.35, 3: 0.45}
        self.trained = False

    def _extraer_pares(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Extrae secuencias de pares inicial y final del historial"""
        pares_iniciales = []
        pares_finales = []

        for _, row in df.iterrows():
            n1, n2, n3 = int(row['n1']), int(row['n2']), int(row['n3'])
            par_ini = f"{n1}{n2}"
            par_fin = f"{n2}{n3}"
            pares_iniciales.append(par_ini)
            pares_finales.append(par_fin)

        return pares_iniciales, pares_finales

    def entrenar(self, df: pd.DataFrame):
        """Entrena las matrices de transicion para ambos tipos de pares"""
        logger.info(f"MarkovPares: Entrenando con orden 1-{self.orden_max}...")

        pares_iniciales, pares_finales = self._extraer_pares(df)

        # Entrenar para par_inicial
        for orden in range(1, self.orden_max + 1):
            for i in range(orden, len(pares_iniciales)):
                estado = tuple(pares_iniciales[i-orden:i])
                siguiente = pares_iniciales[i]
                self.transiciones_inicial[orden][estado][siguiente] += 1

        # Entrenar para par_final
        for orden in range(1, self.orden_max + 1):
            for i in range(orden, len(pares_finales)):
                estado = tuple(pares_finales[i-orden:i])
                siguiente = pares_finales[i]
                self.transiciones_final[orden][estado][siguiente] += 1

        self.trained = True
        logger.info(f"MarkovPares: Entrenamiento completo. "
                   f"Inicial: {len(self.transiciones_inicial[1])} estados O1. "
                   f"Final: {len(self.transiciones_final[1])} estados O1.")

    def predecir_probabilidades(self, tipo: str, historia: List[str]) -> Dict[str, float]:
        """
        Retorna probabilidades para cada par 00-99 usando ensemble de ordenes.

        Args:
            tipo: 'inicial' o 'final'
            historia: Lista de pares recientes
        """
        if not self.trained:
            return {f"{i:02d}": 0.01 for i in range(100)}

        transiciones = self.transiciones_inicial if tipo == 'inicial' else self.transiciones_final
        probs_combined = defaultdict(float)

        for orden in range(1, self.orden_max + 1):
            if len(historia) >= orden:
                estado = tuple(historia[-orden:])
                trans = transiciones[orden].get(estado, Counter())
                total = sum(trans.values())

                if total > 0:
                    # Suavizado Laplace
                    for par_idx in range(100):
                        par = f"{par_idx:02d}"
                        prob = (trans.get(par, 0) + 1) / (total + 100)
                        probs_combined[par] += prob * self.pesos_orden[orden]

        # Normalizar
        total_prob = sum(probs_combined.values())
        if total_prob > 0:
            return {k: v / total_prob for k, v in probs_combined.items()}

        return {f"{i:02d}": 0.01 for i in range(100)}

    def predecir_top_pares(self, tipo: str, historia: List[str], n_top: int = 5) -> List[Dict]:
        """
        Retorna los top N pares mas probables.

        Args:
            tipo: 'inicial' o 'final'
            historia: Lista de pares recientes
            n_top: Cantidad de pares a retornar
        """
        probs = self.predecir_probabilidades(tipo, historia)
        ranking = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        return [
            {'par': par, 'probabilidad': round(prob * 100, 2)}
            for par, prob in ranking[:n_top]
        ]


# =============================================================================
# 2. MARKOV TERMINACION - Especializado en el ultimo digito
# =============================================================================
class MarkovTerminacion:
    """
    Modelo especializado para predecir la terminacion (n3).

    Caracteristicas:
    - Modelos separados por franja (DIA/TARDE/NOCHE)
    - Correlaciones: P(n3|n1), P(n3|n2), P(n3|n1n2)
    - Cadenas de Markov de orden 1-3 para secuencias de n3
    """

    def __init__(self, orden_max: int = 3):
        self.orden_max = orden_max

        # Transiciones Markov por franja
        self.transiciones_por_franja = {
            franja: {orden: defaultdict(Counter) for orden in range(1, orden_max + 1)}
            for franja in ['DIA', 'TARDE', 'NOCHE']
        }

        # Correlaciones condicionales
        self.correlacion_n3_dado_n1 = defaultdict(Counter)  # P(n3|n1)
        self.correlacion_n3_dado_n2 = defaultdict(Counter)  # P(n3|n2)
        self.correlacion_n3_dado_n1n2 = defaultdict(Counter)  # P(n3|n1,n2)

        # Frecuencias por franja
        self.frecuencia_por_franja = {
            franja: Counter() for franja in ['DIA', 'TARDE', 'NOCHE']
        }

        self.pesos_orden = {1: 0.20, 2: 0.35, 3: 0.45}
        self.trained = False

    def entrenar(self, df: pd.DataFrame):
        """Entrena el modelo de terminacion con correlaciones"""
        logger.info("MarkovTerminacion: Entrenando modelos por franja...")

        # Asegurar columna de franja
        if 'momento' in df.columns:
            df = df.copy()
            df['franja'] = df['momento']
        elif 'franja' not in df.columns:
            df = df.copy()
            df['franja'] = df['hora'].map(lambda h: FRANJAS.get(h, 'DIA'))

        # 1. Entrenar correlaciones globales
        for _, row in df.iterrows():
            n1, n2, n3 = int(row['n1']), int(row['n2']), int(row['n3'])

            self.correlacion_n3_dado_n1[n1][n3] += 1
            self.correlacion_n3_dado_n2[n2][n3] += 1
            self.correlacion_n3_dado_n1n2[(n1, n2)][n3] += 1

        # 2. Entrenar Markov y frecuencias por franja
        for franja in ['DIA', 'TARDE', 'NOCHE']:
            df_franja = df[df['franja'] == franja].copy()
            if len(df_franja) < 50:
                logger.warning(f"MarkovTerminacion: Franja {franja} con pocos datos ({len(df_franja)})")
                continue

            secuencia_n3 = df_franja['n3'].astype(int).tolist()

            # Frecuencias
            for n3 in secuencia_n3:
                self.frecuencia_por_franja[franja][n3] += 1

            # Markov por franja
            for orden in range(1, self.orden_max + 1):
                for i in range(orden, len(secuencia_n3)):
                    estado = tuple(secuencia_n3[i-orden:i])
                    siguiente = secuencia_n3[i]
                    self.transiciones_por_franja[franja][orden][estado][siguiente] += 1

        self.trained = True
        logger.info("MarkovTerminacion: Entrenamiento completo.")

    def predecir_probabilidades(self, franja: str, historia_n3: List[int],
                                n1_actual: int = None, n2_actual: int = None) -> Dict[int, float]:
        """
        Predice probabilidades para cada digito 0-9 como terminacion.

        Combina:
        - Markov secuencial (40%)
        - Correlaciones condicionales (35%)
        - Frecuencia por franja (25%)
        """
        if not self.trained:
            return {i: 0.1 for i in range(10)}

        probs = defaultdict(float)

        # 1. MARKOV SECUENCIAL (40%)
        markov_probs = defaultdict(float)
        for orden in range(1, self.orden_max + 1):
            if len(historia_n3) >= orden:
                estado = tuple(historia_n3[-orden:])
                trans = self.transiciones_por_franja[franja][orden].get(estado, Counter())
                total = sum(trans.values())

                if total > 0:
                    for digito in range(10):
                        prob = (trans.get(digito, 0) + 1) / (total + 10)
                        markov_probs[digito] += prob * self.pesos_orden[orden]

        # Normalizar markov
        total_markov = sum(markov_probs.values())
        if total_markov > 0:
            for d in range(10):
                probs[d] += (markov_probs[d] / total_markov) * 0.40

        # 2. CORRELACIONES CONDICIONALES (35%)
        if n1_actual is not None and n2_actual is not None:
            # P(n3|n1,n2) es la mas especifica
            trans_n1n2 = self.correlacion_n3_dado_n1n2.get((n1_actual, n2_actual), Counter())
            total_n1n2 = sum(trans_n1n2.values())

            if total_n1n2 > 5:  # Solo si hay suficiente evidencia
                for digito in range(10):
                    prob = (trans_n1n2.get(digito, 0) + 1) / (total_n1n2 + 10)
                    probs[digito] += prob * 0.35
            else:
                # Fallback a correlaciones individuales
                trans_n1 = self.correlacion_n3_dado_n1.get(n1_actual, Counter())
                trans_n2 = self.correlacion_n3_dado_n2.get(n2_actual, Counter())
                total_n1 = sum(trans_n1.values())
                total_n2 = sum(trans_n2.values())

                for digito in range(10):
                    p_n1 = (trans_n1.get(digito, 0) + 1) / (total_n1 + 10) if total_n1 > 0 else 0.1
                    p_n2 = (trans_n2.get(digito, 0) + 1) / (total_n2 + 10) if total_n2 > 0 else 0.1
                    probs[digito] += (p_n1 * 0.5 + p_n2 * 0.5) * 0.35

        # 3. FRECUENCIA POR FRANJA (25%)
        freq_franja = self.frecuencia_por_franja[franja]
        total_freq = sum(freq_franja.values())

        if total_freq > 0:
            for digito in range(10):
                prob = (freq_franja.get(digito, 0) + 1) / (total_freq + 10)
                probs[digito] += prob * 0.25

        # Normalizar resultado final
        total_prob = sum(probs.values())
        if total_prob > 0:
            return {k: v / total_prob for k, v in probs.items()}

        return {i: 0.1 for i in range(10)}

    def predecir_top_terminaciones(self, franja: str, historia_n3: List[int],
                                    n1_actual: int = None, n2_actual: int = None,
                                    n_top: int = 3) -> List[Dict]:
        """Retorna los top N digitos mas probables como terminacion"""
        probs = self.predecir_probabilidades(franja, historia_n3, n1_actual, n2_actual)
        ranking = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        return [
            {'digito': digito, 'probabilidad': round(prob * 100, 2)}
            for digito, prob in ranking[:n_top]
        ]


# =============================================================================
# 3. MODELO RF ESPECIALIZADO EN PARES
# =============================================================================
class RFPares:
    """Random Forest especializado en clasificar pares (00-99)"""

    def __init__(self, tipo: str = 'inicial'):
        self.tipo = tipo  # 'inicial' o 'final'
        self.modelo = None
        self.scaler = StandardScaler()
        self.feature_cols = []
        self.trained = False

    def _generar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features especializados para prediccion de pares"""
        df = df.copy()

        # Target: par como numero 0-99
        if self.tipo == 'inicial':
            df['target_par'] = df['n1'] * 10 + df['n2']
        else:
            df['target_par'] = df['n2'] * 10 + df['n3']

        # Features de lag (pares anteriores)
        for lag in range(1, 11):
            if self.tipo == 'inicial':
                df[f'par_lag{lag}'] = (df['n1'].shift(lag) * 10 + df['n2'].shift(lag))
            else:
                df[f'par_lag{lag}'] = (df['n2'].shift(lag) * 10 + df['n3'].shift(lag))

        # Features de digitos individuales (lag)
        for pos in ['n1', 'n2', 'n3']:
            for lag in range(1, 6):
                df[f'{pos}_lag{lag}'] = df[pos].shift(lag)

        # Rolling stats del par
        for window in [10, 20, 50]:
            df[f'par_rolling_mean_{window}'] = df['target_par'].rolling(window).mean()
            df[f'par_rolling_std_{window}'] = df['target_par'].rolling(window).std()

        # Features temporales
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['dia_semana'] = df['fecha'].dt.dayofweek
            df['hora_num'] = df['fecha'].dt.hour

        # Features de patron del par
        df['par_suma'] = (df['target_par'] // 10) + (df['target_par'] % 10)
        df['par_es_repetido'] = ((df['target_par'] // 10) == (df['target_par'] % 10)).astype(int)
        df['par_es_consecutivo'] = (abs((df['target_par'] // 10) - (df['target_par'] % 10)) == 1).astype(int)

        # Recencia del par actual
        def calcular_recencia(serie, window=100):
            """Sorteos desde la ultima aparicion de cada valor"""
            recencias = []
            for i in range(len(serie)):
                if i < 1:
                    recencias.append(window)
                    continue
                val = serie.iloc[i]
                found = False
                for j in range(1, min(i+1, window)):
                    if serie.iloc[i-j] == val:
                        recencias.append(j)
                        found = True
                        break
                if not found:
                    recencias.append(window)
            return recencias

        df['par_recencia'] = calcular_recencia(df['target_par'])

        return df

    def entrenar(self, df: pd.DataFrame) -> bool:
        """Entrena el modelo RF para prediccion de pares"""
        logger.info(f"RFPares ({self.tipo}): Generando features...")

        df_features = self._generar_features(df)

        # Definir columnas de features
        exclude = ['n1', 'n2', 'n3', 'fecha', 'sorteo', 'target_par', 'combinacion',
                   'EXACTA_GANADORES', 'EXACTA_MONTO', 'momento', 'dia_semana',
                   'TRIO_PAR_GANADORES', 'TRIO_PAR_MONTO', 'TRIO_AZAR_GANADORES',
                   'TRIO_AZAR_MONTO', 'PAR_GANADORES', 'PAR_MONTO',
                   'TERMINACION_GANADORES', 'TERMINACION_MONTO', 'franja', 'hora']

        self.feature_cols = [c for c in df_features.columns
                            if c not in exclude and df_features[c].dtype in ['int64', 'float64']]

        # Limpiar NaN
        df_clean = df_features.dropna(subset=self.feature_cols + ['target_par'])

        if len(df_clean) < 100:
            logger.warning(f"RFPares ({self.tipo}): Datos insuficientes ({len(df_clean)})")
            return False

        X = df_clean[self.feature_cols].values
        y = df_clean['target_par'].astype(int).values

        # Split temporal
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Escalar
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Entrenar RF
        logger.info(f"RFPares ({self.tipo}): Entrenando RF con {len(X_train)} muestras...")
        self.modelo = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_leaf=5,
            max_features='sqrt',
            n_jobs=-1,
            random_state=42
        )
        self.modelo.fit(X_train_scaled, y_train)

        # Evaluar
        score = self.modelo.score(X_test_scaled, y_test)
        logger.info(f"RFPares ({self.tipo}): Test accuracy = {score:.4f}")

        self.trained = True
        return True

    def predecir_probabilidades(self, features: np.ndarray) -> Dict[int, float]:
        """Retorna probabilidades para cada par 0-99"""
        if not self.trained or self.modelo is None:
            return {i: 0.01 for i in range(100)}

        X_scaled = self.scaler.transform(features.reshape(1, -1))
        probs = self.modelo.predict_proba(X_scaled)[0]
        clases = self.modelo.classes_

        result = {i: 0.001 for i in range(100)}  # Base muy baja
        for clase, prob in zip(clases, probs):
            result[int(clase)] = prob

        return result


# =============================================================================
# 4. LOTO3 ESPECIALISTA - ENSEMBLE PRINCIPAL
# =============================================================================
class Loto3Especialista:
    """
    Ensemble especializado en predicciones PAR y TERMINACION.

    Pesos del ensemble:
    - Markov: 40%
    - RF: 35%
    - Frecuencia: 25%

    Genera:
    - Top 5 pares iniciales
    - Top 5 pares finales
    - Top 3 terminaciones
    """

    def __init__(self):
        self.markov_pares = MarkovPares(orden_max=3)
        self.markov_terminacion = MarkovTerminacion(orden_max=3)
        self.rf_par_inicial = RFPares(tipo='inicial')
        self.rf_par_final = RFPares(tipo='final')

        self.df = None
        self.trained = False

        # Pesos del ensemble
        self.pesos = {
            'markov': 0.40,
            'rf': 0.35,
            'frecuencia': 0.25
        }

    def cargar_datos(self) -> pd.DataFrame:
        """Carga el CSV maestro de LOTO3"""
        if not os.path.exists(RUTA_CSV):
            raise FileNotFoundError(f"No se encuentra {RUTA_CSV}")

        df = pd.read_csv(RUTA_CSV)

        # Asegurar tipos
        for col in ['n1', 'n2', 'n3']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df = df.sort_values('fecha').reset_index(drop=True)

        # Franja
        if 'momento' in df.columns:
            df['franja'] = df['momento']
        elif 'hora' in df.columns:
            df['franja'] = df['hora'].map(lambda h: FRANJAS.get(h, 'DIA'))
        else:
            df['franja'] = 'DIA'

        logger.info(f"Datos cargados: {len(df)} sorteos")
        return df

    def entrenar(self):
        """Entrena todos los modelos del ensemble"""
        logger.info("=" * 60)
        logger.info("LOTO3 ESPECIALISTA: ENTRENAMIENTO")
        logger.info("=" * 60)

        self.df = self.cargar_datos()

        # 1. Entrenar Markov de pares
        self.markov_pares.entrenar(self.df)

        # 2. Entrenar Markov de terminacion
        self.markov_terminacion.entrenar(self.df)

        # 3. Entrenar RF de pares (opcional, puede fallar con pocos datos)
        try:
            self.rf_par_inicial.entrenar(self.df)
        except Exception as e:
            logger.warning(f"RF par_inicial no entrenado: {e}")

        try:
            self.rf_par_final.entrenar(self.df)
        except Exception as e:
            logger.warning(f"RF par_final no entrenado: {e}")

        self.trained = True
        logger.info("ENTRENAMIENTO COMPLETO")

        # Guardar modelos
        self._guardar_modelos()

    def _guardar_modelos(self):
        """Guarda los modelos entrenados"""
        try:
            joblib.dump(self.markov_pares, os.path.join(RUTA_MODELOS, 'markov_pares.pkl'))
            joblib.dump(self.markov_terminacion, os.path.join(RUTA_MODELOS, 'markov_terminacion.pkl'))

            if self.rf_par_inicial.trained:
                joblib.dump(self.rf_par_inicial, os.path.join(RUTA_MODELOS, 'rf_par_inicial.pkl'))
            if self.rf_par_final.trained:
                joblib.dump(self.rf_par_final, os.path.join(RUTA_MODELOS, 'rf_par_final.pkl'))

            logger.info(f"Modelos guardados en {RUTA_MODELOS}")
        except Exception as e:
            logger.error(f"Error guardando modelos: {e}")

    def _cargar_modelos(self) -> bool:
        """Intenta cargar modelos previamente entrenados"""
        try:
            path_markov_pares = os.path.join(RUTA_MODELOS, 'markov_pares.pkl')
            path_markov_term = os.path.join(RUTA_MODELOS, 'markov_terminacion.pkl')

            if os.path.exists(path_markov_pares):
                self.markov_pares = joblib.load(path_markov_pares)
            if os.path.exists(path_markov_term):
                self.markov_terminacion = joblib.load(path_markov_term)

            # RF son opcionales
            path_rf_ini = os.path.join(RUTA_MODELOS, 'rf_par_inicial.pkl')
            path_rf_fin = os.path.join(RUTA_MODELOS, 'rf_par_final.pkl')

            if os.path.exists(path_rf_ini):
                self.rf_par_inicial = joblib.load(path_rf_ini)
            if os.path.exists(path_rf_fin):
                self.rf_par_final = joblib.load(path_rf_fin)

            self.trained = True
            return True
        except Exception as e:
            logger.warning(f"No se pudieron cargar modelos: {e}")
            return False

    def _calcular_frecuencias_pares(self, window: int = 50) -> Tuple[Dict, Dict]:
        """Calcula frecuencias recientes de pares"""
        if self.df is None:
            return {}, {}

        ultimos = self.df.tail(window)

        freq_inicial = Counter()
        freq_final = Counter()

        for _, row in ultimos.iterrows():
            n1, n2, n3 = int(row['n1']), int(row['n2']), int(row['n3'])
            freq_inicial[f"{n1}{n2}"] += 1
            freq_final[f"{n2}{n3}"] += 1

        # Normalizar a probabilidades
        total_ini = sum(freq_inicial.values())
        total_fin = sum(freq_final.values())

        prob_inicial = {f"{i:02d}": (freq_inicial.get(f"{i:02d}", 0) + 1) / (total_ini + 100)
                       for i in range(100)}
        prob_final = {f"{i:02d}": (freq_final.get(f"{i:02d}", 0) + 1) / (total_fin + 100)
                     for i in range(100)}

        return prob_inicial, prob_final

    def _calcular_frecuencias_terminacion(self, franja: str, window: int = 50) -> Dict[int, float]:
        """Calcula frecuencias recientes de terminacion por franja"""
        if self.df is None:
            return {i: 0.1 for i in range(10)}

        df_franja = self.df[self.df['franja'] == franja].tail(window)
        freq = Counter(df_franja['n3'].astype(int))
        total = sum(freq.values())

        return {i: (freq.get(i, 0) + 1) / (total + 10) for i in range(10)}

    def predecir(self, franja: str = None, n_pares: int = 5, n_terminaciones: int = 3) -> Dict:
        """
        Genera predicciones especializadas para PAR y TERMINACION.

        Args:
            franja: 'DIA', 'TARDE', 'NOCHE' (auto-detecta si None)
            n_pares: Cantidad de pares a retornar (por tipo)
            n_terminaciones: Cantidad de terminaciones a retornar

        Returns:
            Dict con pares_inicial, pares_final, terminaciones y metadata
        """
        if not self.trained:
            if not self._cargar_modelos():
                logger.info("Entrenando modelos...")
                self.entrenar()

        # Recargar datos frescos
        if self.df is None:
            self.df = self.cargar_datos()

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

        # Obtener historias recientes
        ultimos = self.df.tail(20)
        historia_par_inicial = [f"{int(r['n1'])}{int(r['n2'])}" for _, r in ultimos.iterrows()]
        historia_par_final = [f"{int(r['n2'])}{int(r['n3'])}" for _, r in ultimos.iterrows()]
        historia_n3 = ultimos['n3'].astype(int).tolist()

        # Ultimos n1, n2 conocidos (para correlaciones de terminacion)
        ultimo_n1 = int(self.df['n1'].iloc[-1])
        ultimo_n2 = int(self.df['n2'].iloc[-1])

        # =====================================================================
        # PREDICCION DE PARES INICIALES
        # =====================================================================
        probs_par_inicial = defaultdict(float)

        # 1. Markov (40%)
        markov_probs_ini = self.markov_pares.predecir_probabilidades('inicial', historia_par_inicial)
        for par, prob in markov_probs_ini.items():
            probs_par_inicial[par] += prob * self.pesos['markov']

        # 2. RF (35%)
        if self.rf_par_inicial.trained:
            df_features = self.rf_par_inicial._generar_features(self.df)
            ultima_fila = df_features[self.rf_par_inicial.feature_cols].iloc[-1].values
            rf_probs_ini = self.rf_par_inicial.predecir_probabilidades(ultima_fila)
            for par_int, prob in rf_probs_ini.items():
                probs_par_inicial[f"{par_int:02d}"] += prob * self.pesos['rf']

        # 3. Frecuencia (25%)
        freq_ini, freq_fin = self._calcular_frecuencias_pares()
        for par, prob in freq_ini.items():
            probs_par_inicial[par] += prob * self.pesos['frecuencia']

        # Ranking pares iniciales
        ranking_ini = sorted(probs_par_inicial.items(), key=lambda x: x[1], reverse=True)
        pares_inicial = [
            {'par': par, 'score': round(prob * 100, 2)}
            for par, prob in ranking_ini[:n_pares]
        ]

        # =====================================================================
        # PREDICCION DE PARES FINALES
        # =====================================================================
        probs_par_final = defaultdict(float)

        # 1. Markov (40%)
        markov_probs_fin = self.markov_pares.predecir_probabilidades('final', historia_par_final)
        for par, prob in markov_probs_fin.items():
            probs_par_final[par] += prob * self.pesos['markov']

        # 2. RF (35%)
        if self.rf_par_final.trained:
            df_features = self.rf_par_final._generar_features(self.df)
            ultima_fila = df_features[self.rf_par_final.feature_cols].iloc[-1].values
            rf_probs_fin = self.rf_par_final.predecir_probabilidades(ultima_fila)
            for par_int, prob in rf_probs_fin.items():
                probs_par_final[f"{par_int:02d}"] += prob * self.pesos['rf']

        # 3. Frecuencia (25%)
        for par, prob in freq_fin.items():
            probs_par_final[par] += prob * self.pesos['frecuencia']

        # Ranking pares finales
        ranking_fin = sorted(probs_par_final.items(), key=lambda x: x[1], reverse=True)
        pares_final = [
            {'par': par, 'score': round(prob * 100, 2)}
            for par, prob in ranking_fin[:n_pares]
        ]

        # =====================================================================
        # PREDICCION DE TERMINACIONES
        # =====================================================================
        probs_terminacion = defaultdict(float)

        # 1. Markov (40%)
        markov_probs_term = self.markov_terminacion.predecir_probabilidades(
            franja, historia_n3, ultimo_n1, ultimo_n2
        )
        for digito, prob in markov_probs_term.items():
            probs_terminacion[digito] += prob * self.pesos['markov']

        # 2. Correlaciones (ya incluidas en markov_terminacion, pero agregamos RF weight)
        # RF no aplica directamente a terminacion, usamos las correlaciones como proxy
        # El peso de RF se redistribuye a frecuencia

        # 3. Frecuencia (25% + 35% de RF = 60% para terminacion)
        freq_term = self._calcular_frecuencias_terminacion(franja)
        for digito, prob in freq_term.items():
            probs_terminacion[digito] += prob * 0.60  # markov + frecuencia boosted

        # Ranking terminaciones
        ranking_term = sorted(probs_terminacion.items(), key=lambda x: x[1], reverse=True)
        terminaciones = [
            {'digito': digito, 'score': round(prob * 100, 2)}
            for digito, prob in ranking_term[:n_terminaciones]
        ]

        return {
            'franja': franja,
            'pares_inicial': pares_inicial,
            'pares_final': pares_final,
            'terminaciones': terminaciones,
            'timestamp': datetime.now(TZ_CHILE).strftime("%Y-%m-%d %H:%M:%S")
        }


# =============================================================================
# 5. FUNCIONES DE PERSISTENCIA
# =============================================================================
def calcular_proximo_sorteo_loto3() -> Tuple[int, datetime]:
    """Calcula el proximo sorteo de LOTO3"""
    ahora = datetime.now(TZ_CHILE)

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


def guardar_en_simulaciones(predicciones: List[Dict]):
    """Guarda las predicciones en LOTO_SIMULACIONES.csv"""
    nuevas_filas = []
    for p in predicciones:
        fila = {
            'id': p['id'],
            'fecha_generacion': p['fecha_generacion'],
            'juego': p['juego'],
            'numeros': p['numeros'],
            'sorteo_objetivo': p['sorteo_objetivo'],
            'estado': p['estado'],
            'aciertos': p['aciertos'],
            'score_afinidad': p['score_afinidad'],
            'hora_dia': p.get('hora_dia', 0),
            'algoritmo': p['algoritmo'],
            'nota_especial': p.get('nota_especial', ''),
            'fecha_lanzamiento': p['fecha_lanzamiento'],
            'modalidad': p.get('modalidad', 'EXACTA')
        }
        nuevas_filas.append(fila)

    df_new = pd.DataFrame(nuevas_filas)

    # Leer CSV existente para obtener columnas actuales
    if os.path.exists(RUTA_SIMULACIONES):
        try:
            # Leer solo el header para ver las columnas
            df_existing = pd.read_csv(RUTA_SIMULACIONES, nrows=0)
            columnas_existentes = list(df_existing.columns)

            # Si no existe la columna modalidad, la agregamos al CSV existente
            if 'modalidad' not in columnas_existentes:
                columnas_existentes.append('modalidad')
                # Reescribir el CSV con la nueva columna
                df_full = pd.read_csv(RUTA_SIMULACIONES)
                df_full['modalidad'] = ''  # Valor vacio para filas existentes
                df_full.to_csv(RUTA_SIMULACIONES, index=False)
                logger.info("Columna 'modalidad' agregada al CSV existente")

            # Ordenar df_new segun columnas existentes
            for col in columnas_existentes:
                if col not in df_new.columns:
                    df_new[col] = ''

            df_new = df_new[columnas_existentes]
            df_new.to_csv(RUTA_SIMULACIONES, mode='a', header=False, index=False)

        except Exception as e:
            logger.error(f"Error leyendo CSV existente: {e}. Creando nuevo.")
            columnas = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo',
                        'estado', 'aciertos', 'score_afinidad', 'hora_dia',
                        'algoritmo', 'nota_especial', 'fecha_lanzamiento', 'modalidad']
            df_new = df_new.reindex(columns=columnas, fill_value='')
            df_new.to_csv(RUTA_SIMULACIONES, mode='w', header=True, index=False)
    else:
        columnas = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo',
                    'estado', 'aciertos', 'score_afinidad', 'hora_dia',
                    'algoritmo', 'nota_especial', 'fecha_lanzamiento', 'modalidad']
        df_new = df_new.reindex(columns=columnas, fill_value='')
        df_new.to_csv(RUTA_SIMULACIONES, mode='w', header=True, index=False)

    logger.info(f"Guardadas {len(nuevas_filas)} predicciones especializadas en LOTO_SIMULACIONES.csv")


def ejecutar_loto3_especialista(guardar: bool = True) -> List[Dict]:
    """
    Funcion principal: Ejecuta el sistema LOTO3 Especialista.

    Returns:
        Lista de predicciones generadas (PAR_INICIAL, PAR_FINAL, TERMINACION)
    """
    logger.info("=" * 60)
    logger.info("LOTO3 ESPECIALISTA v1.0 - PAR & TERMINACION")
    logger.info("=" * 60)

    ahora = datetime.now(TZ_CHILE)
    sorteo_objetivo, fecha_sorteo = calcular_proximo_sorteo_loto3()

    logger.info(f"Hora actual: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Sorteo objetivo: #{sorteo_objetivo}")
    logger.info(f"Fecha sorteo: {fecha_sorteo.strftime('%d/%m/%Y %H:%M')}")

    # Determinar franja
    hora_sorteo = fecha_sorteo.hour
    franja = FRANJAS.get(hora_sorteo, 'DIA')

    # Crear y ejecutar especialista
    especialista = Loto3Especialista()

    try:
        resultados = especialista.predecir(franja=franja, n_pares=5, n_terminaciones=3)
    except Exception as e:
        logger.error(f"Error en prediccion: {e}")
        import traceback
        traceback.print_exc()
        return []

    # Formatear predicciones para guardar
    predicciones = []
    base_id = int(time.time())

    # 1. Pares Iniciales
    for i, par in enumerate(resultados['pares_inicial']):
        predicciones.append({
            'id': base_id + i,
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_lanzamiento': fecha_sorteo.strftime('%d/%m/%Y %H:%M'),
            'sorteo_objetivo': sorteo_objetivo,
            'juego': 'LOTO3',
            'numeros': par['par'],
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': par['score'],
            'hora_dia': hora_sorteo,
            'algoritmo': 'loto3_par_inicial_v1',
            'nota_especial': f"Franja:{franja}|Rank:{i+1}",
            'modalidad': 'PAR_INICIAL'
        })
        logger.info(f"  PAR_INICIAL #{i+1}: {par['par']} - Score: {par['score']}")

    # 2. Pares Finales
    for i, par in enumerate(resultados['pares_final']):
        predicciones.append({
            'id': base_id + 100 + i,
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_lanzamiento': fecha_sorteo.strftime('%d/%m/%Y %H:%M'),
            'sorteo_objetivo': sorteo_objetivo,
            'juego': 'LOTO3',
            'numeros': par['par'],
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': par['score'],
            'hora_dia': hora_sorteo,
            'algoritmo': 'loto3_par_final_v1',
            'nota_especial': f"Franja:{franja}|Rank:{i+1}",
            'modalidad': 'PAR_FINAL'
        })
        logger.info(f"  PAR_FINAL #{i+1}: {par['par']} - Score: {par['score']}")

    # 3. Terminaciones
    for i, term in enumerate(resultados['terminaciones']):
        predicciones.append({
            'id': base_id + 200 + i,
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_lanzamiento': fecha_sorteo.strftime('%d/%m/%Y %H:%M'),
            'sorteo_objetivo': sorteo_objetivo,
            'juego': 'LOTO3',
            'numeros': str(term['digito']),
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': term['score'],
            'hora_dia': hora_sorteo,
            'algoritmo': 'loto3_terminacion_v1',
            'nota_especial': f"Franja:{franja}|Rank:{i+1}",
            'modalidad': 'TERMINACION'
        })
        logger.info(f"  TERMINACION #{i+1}: {term['digito']} - Score: {term['score']}")

    if guardar and predicciones:
        guardar_en_simulaciones(predicciones)

    return predicciones


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--entrenar':
        # Modo entrenamiento forzado
        especialista = Loto3Especialista()
        especialista.entrenar()
    else:
        # Modo prediccion normal
        resultados = ejecutar_loto3_especialista(guardar=True)

        if resultados:
            print("\n" + "=" * 50)
            print("PREDICCIONES LOTO3 ESPECIALISTA")
            print("=" * 50)

            print("\nPARES INICIALES (n1n2):")
            for r in resultados:
                if r['modalidad'] == 'PAR_INICIAL':
                    print(f"  {r['numeros']} - Score: {r['score_afinidad']}")

            print("\nPARES FINALES (n2n3):")
            for r in resultados:
                if r['modalidad'] == 'PAR_FINAL':
                    print(f"  {r['numeros']} - Score: {r['score_afinidad']}")

            print("\nTERMINACIONES (n3):")
            for r in resultados:
                if r['modalidad'] == 'TERMINACION':
                    print(f"  {r['numeros']} - Score: {r['score_afinidad']}")
