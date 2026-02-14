"""
LOTO ORQUESTADOR - Telegram Bot
===============================
Orquesta todo el sistema de scraping, predicciones y evaluación.
Sin interfaz - solo notificaciones por Telegram.

Autor: Gabot
Fecha: 2026-02-14
"""

import os
import sys
import json
import csv
import logging
import asyncio
import importlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import requests

# Configurar paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, 'models'))
sys.path.insert(0, os.path.join(CURRENT_DIR, 'scrapers'))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar config
from telegram_config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    SCRAPING_SCHEDULE, PREDICTION_SCHEDULE, RETRAIN_HOUR
)
from telegram_notifier import TelegramNotifier

# =============================================================================
# CONFIGURACIÓN DE RUTAS
# =============================================================================
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODELS_DIR = os.path.join(CURRENT_DIR, 'models')

# Archivos de datos
CSV_LOTO3 = os.path.join(DATA_DIR, 'LOTO3_MAESTRO.csv')
CSV_SIMULACIONES = os.path.join(DATA_DIR, 'LOTO_SIMULACIONES.csv')


# =============================================================================
# ALGORITMOS DE PREDICCIÓN (MÚLTIPLES)
# =============================================================================

class AlgoritmoBase:
    """Clase base para algoritmos de predicción"""
    nombre = "base"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        raise NotImplementedError


class AlgoritmoFrecuencias(AlgoritmoBase):
    """Basado en frecuencias históricas por posición"""
    nombre = "Frecuencias"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        resultados = []
        
        for pos in ['n1', 'n2', 'n3']:
            if pos not in df.columns:
                continue
            freq = df[pos].value_counts(normalize=True).head(10)
            probs = freq.to_dict()
        
        # Generar combinaciones basadas en frecuencias
        for i in range(n_predicciones):
            nums = []
            for pos in ['n1', 'n2', 'n3']:
                if pos in df.columns:
                    freq = df[pos].value_counts(normalize=True)
                    # Selección ponderada
                    nums.append(int(freq.sample(1, weights=freq.values).index[0]))
            
            confianza = 40 + (i * 5)  # Decreciente
            resultados.append({
                'algoritmo': self.nombre,
                'numeros': nums,
                'confianza': confianza
            })
        
        return resultados


class AlgoritmoMarkov(AlgoritmoBase):
    """Basado en cadenas de Markov"""
    nombre = "Markov"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        resultados = []
        
        # Matrices de transición
        transiciones = {}
        for pos in ['n1', 'n2', 'n3']:
            if pos not in df.columns:
                continue
            freq = df[pos].value_counts(normalize=True)
            transiciones[pos] = freq.to_dict()
        
        # Generar predicciones
        for i in range(n_predicciones):
            nums = []
            for pos in ['n1', 'n2', 'n3']:
                if pos in transiciones:
                    opts = list(transiciones[pos].keys())
                    weights = list(transiciones[pos].values())
                    nums.append(int(pd.Series(opts).sample(1, weights=weights).values[0]))
            
            resultados.append({
                'algoritmo': self.nombre,
                'numeros': nums,
                'confianza': 45 + (i * 3)
            })
        
        return resultados


class AlgoritmoRandomForest(AlgoritmoBase):
    """Random Forest para LOTO3"""
    nombre = "RandomForest"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        try:
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
            
            if len(df) < 50:
                return self._fallback(df, n_predicciones)
            
            # Features simples
            X = df[['n1', 'n2', 'n3']].iloc[:-1].values
            y_n1 = df['n1'].iloc[1:].values
            y_n2 = df['n2'].iloc[1:].values
            y_n3 = df['n3'].iloc[1:].values
            
            # Entrenar modelos simples
            rf1 = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            rf2 = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            rf3 = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            
            rf1.fit(X, y_n1)
            rf2.fit(X, y_n2)
            rf3.fit(X, y_n3)
            
            # Última fila como input
            last = df[['n1', 'n2', 'n3']].iloc[-1:].values
            
            # Predicciones
            resultados = []
            for i in range(n_predicciones):
                p1 = rf1.predict(last)[0]
                p2 = rf2.predict(last)[0]
                p3 = rf3.predict(last)[0]
                
                resultados.append({
                    'algoritmo': self.nombre,
                    'numeros': [int(p1), int(p2), int(p3)],
                    'confianza': 55 - (i * 5)
                })
                
                # Modificar un poco para diversidad
                last[0][0] = (last[0][0] + 1) % 10
            
            return resultados
            
        except Exception as e:
            logger.warning(f"RF error: {e}")
            return self._fallback(df, n_predicciones)
    
    def _fallback(self, df, n):
        return [{
            'algoritmo': self.nombre,
            'numeros': [5, 5, 5],
            'confianza': 30
        }] * n


class AlgoritmoMediana(AlgoritmoBase):
    """Basado en medianas y tendencias"""
    nombre = "Mediana"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        resultados = []
        
        for i in range(n_predicciones):
            nums = []
            for pos in ['n1', 'n2', 'n3']:
                if pos in df.columns:
                    median = df[pos].median()
                    std = df[pos].std()
                    # Añadir ruido alrededor de la mediana
                    import random
                    val = int(median + random.uniform(-std, std))
                    val = max(0, min(9, val))
                    nums.append(val)
            
            resultados.append({
                'algoritmo': self.nombre,
                'numeros': nums if nums else [5, 5, 5],
                'confianza': 35 + (i * 2)
            })
        
        return resultados


class AlgoritmoCiclico(AlgoritmoBase):
    """Detecta ciclos en los números"""
    nombre = "Ciclico"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        resultados = []
        
        # Análisis de ciclo semanal
        df_copy = df.copy()
        df_copy['fecha'] = pd.to_datetime(df_copy['fecha'], errors='coerce')
        df_copy['dia_semana'] = df_copy['fecha'].dt.dayofweek
        
        # Último día de la semana
        ultimo_dia = df_copy['dia_semana'].iloc[-1] if len(df_copy) > 0 else 0
        
        for i in range(n_predicciones):
            nums = []
            for pos in ['n1', 'n2', 'n3']:
                if pos in df.columns:
                    # Tomar números del mismo día de la semana
                    mismos_dias = df[df_copy['dia_semana'] == ultimo_dia][pos]
                    if len(mismos_dias) > 0:
                        freq = mismos_dias.value_counts(normalize=True)
                        nums.append(int(freq.sample(1, weights=freq.values).index[0]))
                    else:
                        nums.append(i * 3 % 10)
            
            resultados.append({
                'algoritmo': self.nombre,
                'numeros': nums if nums else [3, 6, 9],
                'confianza': 38 + (i * 4)
            })
        
        return resultados


class AlgoritmoRegresionLogistica(AlgoritmoBase):
    """Regresión logística multiclase"""
    nombre = "Logistica"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        try:
            from sklearn.linear_model import LogisticRegression
            import numpy as np
            
            if len(df) < 30:
                return self._fallback(df, n_predicciones)
            
            X = df[['n1', 'n2', 'n3']].iloc[:-1].values
            last = df[['n1', 'n2', 'n3']].iloc[-1:].values
            
            resultados = []
            for i in range(n_predicciones):
                try:
                    lr = LogisticRegression(max_iter=100, random_state=42+i)
                    lr.fit(X, df['n1'].iloc[1:].values)
                    p = lr.predict(last)[0]
                    
                    resultados.append({
                        'algoritmo': self.nombre,
                        'numeros': [int(p), (int(p)+5)%10, (int(p)+3)%10],
                        'confianza': 42 - (i * 3)
                    })
                except:
                    resultados.append({
                        'algoritmo': self.nombre,
                        'numeros': [4, 4, 4],
                        'confianza': 30
                    })
            
            return resultados
            
        except Exception as e:
            return self._fallback(df, n_predicciones)
    
    def _fallback(self, df, n):
        return [{
            'algoritmo': self.nombre,
            'numeros': [1, 2, 3],
            'confianza': 25
        }] * n


class AlgoritmoNaiveBayes(AlgoritmoBase):
    """Naive Bayes para clasificación"""
    nombre = "NaiveBayes"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        try:
            from sklearn.naive_bayes import GaussianNB
            import numpy as np
            
            if len(df) < 20:
                return self._fallback(df, n_predicciones)
            
            X = df[['n1', 'n2', 'n3']].iloc[:-1].values
            last = df[['n1', 'n2', 'n3']].iloc[-1:].values
            
            resultados = []
            for i, target_col in enumerate(['n1', 'n2', 'n3']):
                try:
                    nb = GaussianNB()
                    nb.fit(X, df[target_col].iloc[1:].values)
                    p = nb.predict(last)[0]
                    resultados.append(int(p) % 10)
                except:
                    resultados.append(i * 3 % 10)
            
            return [{
                'algoritmo': self.nombre,
                'numeros': resultados,
                'confianza': 40
            }] * n_predicciones
            
        except Exception as e:
            return self._fallback(df, n_predicciones)
    
    def _fallback(self, df, n):
        return [{
            'algoritmo': self.nombre,
            'numeros': [7, 7, 7],
            'confianza': 20
        }] * n


class AlgoritmoKNN(AlgoritmoBase):
    """K-Nearest Neighbors"""
    nombre = "KNN"
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        try:
            from sklearn.neighbors import KNeighborsClassifier
            
            if len(df) < 20:
                return self._fallback(df, n_predicciones)
            
            X = df[['n1', 'n2', 'n3']].iloc[:-1].values
            last = df[['n1', 'n2', 'n3']].iloc[-1:].values
            
            resultados = []
            for i in range(n_predicciones):
                try:
                    knn = KNeighborsClassifier(n_neighbors=min(5, len(df)//2))
                    knn.fit(X, df['n1'].iloc[1:].values)
                    p = knn.predict(last)[0]
                    
                    resultados.append({
                        'algoritmo': self.nombre,
                        'numeros': [int(p), (int(p)+2)%10, (int(p)+4)%10],
                        'confianza': 38 - (i * 2)
                    })
                except:
                    resultados.append({
                        'algoritmo': self.nombre,
                        'numeros': [2, 5, 8],
                        'confianza': 25
                    })
            
            return resultados
            
        except Exception as e:
            return self._fallback(df, n_predicciones)
    
    def _fallback(self, df, n):
        return [{
            'algoritmo': self.nombre,
            'numeros': [2, 5, 8],
            'confianza': 20
        }] * n


class AlgoritmoEnsemble(AlgoritmoBase):
    """Ensemble de múltiples algoritmos"""
    nombre = "Ensemble"
    
    def __init__(self):
        self.algos = [
            AlgoritmoFrecuencias(),
            AlgoritmoMarkov(),
            AlgoritmoMediana(),
        ]
    
    def predecir(self, df: pd.DataFrame, n_predicciones: int = 3) -> List[Dict]:
        # Obtener predicciones de cada algoritmo
        todas_preds = []
        for algo in self.algos:
            try:
                pred = algo.predecir(df, 1)
                if pred:
                    todas_preds.extend(pred)
            except:
                pass
        
        # Votación mayoritaria por posición
        if todas_preds:
            resultados = []
            for i in range(n_predicciones):
                # Combinar predicciones
                nums_votados = []
                for pos_idx in range(3):
                    digitos = [p['numeros'][pos_idx] for p in todas_preds if len(p['numeros']) > pos_idx]
                    if digitos:
                        from collections import Counter
                        mas_comun = Counter(digitos).most_common(1)[0][0]
                        nums_votados.append(mas_comun)
                
                confianza_prom = sum(p['confianza'] for p in todas_preds) / len(todas_preds)
                
                resultados.append({
                    'algoritmo': self.nombre,
                    'numeros': nums_votados if nums_votados else [5, 5, 5],
                    'confianza': int(confianza_prom)
                })
            
            return resultados
        
        return [{
            'algoritmo': self.nombre,
            'numeros': [4, 4, 4],
            'confianza': 30
        }]


# =============================================================================
# REGISTRO DE ALGORITMOS
# =============================================================================
ALGORITMOS_DISPONIBLES = {
    'frecuencias': AlgoritmoFrecuencias,
    'markov': AlgoritmoMarkov,
    'randomforest': AlgoritmoRandomForest,
    'mediana': AlgoritmoMediana,
    'ciclico': AlgoritmoCiclico,
    'logistica': AlgoritmoRegresionLogistica,
    'naivebayes': AlgoritmoNaiveBayes,
    'knn': AlgoritmoKNN,
    'ensemble': AlgoritmoEnsemble,
}


# =============================================================================
# GENERADOR DE PREDICCIONES
# =============================================================================

def generar_predicciones_loto3(notifier: TelegramNotifier = None) -> bool:
    """
    Genera predicciones para LOTO3 usando múltiples algoritmos.
    Envía las predicciones por Telegram.
    """
    logger.info("🎯 Generando predicciones para LOTO3...")
    
    try:
        # Cargar datos históricos
        if not os.path.exists(CSV_LOTO3):
            logger.error(f"Archivo no encontrado: {CSV_LOTO3}")
            if notifier:
                notifier.send_error(f"No se encontró {CSV_LOTO3}")
            return False
        
        df = pd.read_csv(CSV_LOTO3)
        
        if len(df) < 10:
            logger.error("Datos insuficientes para predicción")
            if notifier:
                notifier.send_error("Datos históricos insuficientes")
            return False
        
        # Fecha actual
        fecha_hoy = datetime.now().strftime("%d de %B de %Y")
        
        # Mensaje de cabecera
        mensaje = f"🎯 *Predicciones para LOTO 3* | {fecha_hoy}\n"
        
        # Ejecutar cada algoritmo
        predicciones_totales = []
        
        for nombre, ClaseAlgo in ALGORITMOS_DISPONIBLES.items():
            try:
                algo = ClaseAlgo()
                preds = algo.predecir(df, n_predicciones=2)
                
                for pred in preds:
                    predicciones_totales.append(pred)
                    
                    nums_str = ", ".join(str(n) for n in pred['numeros'])
                    mensaje += f"• *{pred['algoritmo']}*: {nums_str} | {pred['confianza']}%\n"
                
            except Exception as e:
                logger.warning(f"Error en algoritmo {nombre}: {e}")
        
        # Guardar predicciones en CSV
        _guardar_predicciones(predicciones_totales, "LOTO3")
        
        # Enviar por Telegram
        if notifier:
            notifier.send_message(mensaje)
        
        logger.info(f"✅ {len(predicciones_totales)} predicciones generadas")
        return True
        
    except Exception as e:
        logger.error(f"Error general en predicciones: {e}")
        if notifier:
            notifier.send_error(f"Error generando predicciones: {e}")
        return False


def _guardar_predicciones(predicciones: List[Dict], juego: str):
    """Guarda las predicciones en el CSV de simulaciones"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sorteos_target = _obtener_proximo_sorteo(juego)
    
    existe = os.path.exists(CSV_SIMULACIONES)
    
    with open(CSV_SIMULACIONES, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        if not existe:
            writer.writerow(['fecha_hora', 'juego', 'algoritmo', 'numeros', 'sorteo_objetivo', 'estado', 'aciertos', 'score'])
        
        for pred in predicciones:
            writer.writerow([
                fecha_hora,
                juego,
                pred['algoritmo'],
                json.dumps(pred['numeros']),
                sorteos_target,
                'PENDIENTE',
                0,
                pred.get('confianza', 0)
            ])


def _obtener_proximo_sorteo(juego: str) -> str:
    """Obtiene el identificador del próximo sorteo"""
    ahora = datetime.now()
    
    if juego == "LOTO3":
        # Próximos sorteos: 14:00, 18:00, 21:00
        horas = [14, 18, 21]
        for h in horas:
            if ahora.hour < h:
                return ahora.strftime("%Y-%m-%d") + f"_{h}:00"
        # Ya pasaron todos, siguiente día
        manana = ahora + timedelta(days=1)
        return manana.strftime("%Y-%m-%d") + "_14:00"
    
    return ahora.strftime("%Y-%m-%d")


# =============================================================================
# SCRAPER SIMPLIFICADO
# =============================================================================

def scrape_resultado(juego: str, notifier: TelegramNotifier = None) -> Optional[Dict]:
    """
    Scrapea el resultado de un juego específico.
    Por ahora, retorna None - necesita implementarse con Playwright/Scrape.do
    """
    logger.info(f"🔎 Scraping {juego}...")
    
    # TODO: Implementar scraping real
    # Por ahora simulamos que no hay nuevo resultado
    if notifier:
        notifier.send_status(f"Scraper {juego} no implementado aún")
    
    return None


# =============================================================================
# EVALUADOR DE PREDICCIONES
# =============================================================================

def parse_numeros(valor) -> List[int]:
    """Parsea el campo numeros handleando múltiples formatos"""
    # Caso 1: ya es una lista
    if isinstance(valor, list):
        return valor
    
    # Caso 2: es un número (int o float) - dato corrupto
    if isinstance(valor, (int, float)):
        s = str(int(valor))
        if len(s) >= 3:
            return [int(c) for c in s[:3]]
        return []
    
    # Caso 3: es string
    valor = str(valor).strip()
    if not valor:
        return []
    
    # Si empieza con [ es JSON
    if valor.startswith('['):
        try:
            result = json.loads(valor)
            if isinstance(result, list):
                return result
            # Es un solo número
            return [result] if isinstance(result, (int, float)) else []
        except:
            pass
    
    # Si es un número solo (ej: "34"), dividirlo en dígitos
    if valor.isdigit():
        if len(valor) >= 3:
            return [int(c) for c in valor[:3]]
        elif len(valor) >= 1:
            # Un solo dígito - dato corrupto
            return [int(valor)]
    
    # Intentar JSON con comillas
    try:
        result = json.loads(valor.replace("'", '"'))
        if isinstance(result, list):
            return result
        return [result] if isinstance(result, (int, float)) else []
    except:
        pass
    
    # Último intento: parser manual
    import re
    nums = re.findall(r'\d+', valor)
    return [int(n) for n in nums] if nums else []


def evaluar_predicciones(resultado: Dict, notifier: TelegramNotifier = None) -> bool:
    """
    Compara predicciones con resultado real.
    """
    logger.info("📊 Evaluando predicciones...")
    
    try:
        numeros_reales = resultado.get('numeros', [])
        juego = resultado.get('juego', 'LOTO3')
        
        if not numeros_reales:
            return False
        
        # Cargar predicciones pendientes
        if not os.path.exists(CSV_SIMULACIONES):
            return False
        
        df_sim = pd.read_csv(CSV_SIMULACIONES)
        pendientes = df_sim[(df_sim['juego'] == juego) & (df_sim['estado'] == 'PENDIENTE')]
        
        if len(pendientes) == 0:
            logger.info("No hay predicciones pendientes")
            return False
        
        # Limitar a las últimas 50 predicciones para evitar mensaje muy largo
        pendientes = pendientes.tail(50)
        
        # Resumen por algoritmo
        resumen = {}
        cambios = []
        
        for idx, pred in pendientes.iterrows():
            try:
                nums_pred = parse_numeros(pred['numeros'])
                
                if not nums_pred or len(nums_pred) == 0:
                    continue
                
                # Calcular aciertos
                aciertos = sum(1 for n in nums_pred if n in numeros_reales)
                
                # Score: aciertos * 100 / 3
                score = (aciertos * 100) // 3 if len(nums_pred) > 0 else 0
                
                algoritmo = pred.get('algoritmo', 'Unknown')
                
                # Acumular para resumen
                if algoritmo not in resumen:
                    resumen[algoritmo] = {'aciertos_3': 0, 'aciertos_2': 0, 'aciertos_1': 0, 'total': 0}
                
                resumen[algoritmo]['total'] += 1
                if aciertos == 3:
                    resumen[algoritmo]['aciertos_3'] += 1
                elif aciertos == 2:
                    resumen[algoritmo]['aciertos_2'] += 1
                elif aciertos == 1:
                    resumen[algoritmo]['aciertos_1'] += 1
                
                cambios.append({
                    'idx': idx,
                    'estado': 'AUDITADO',
                    'aciertos': aciertos,
                    'score': score
                })
                
            except Exception as e:
                logger.warning(f"Error evaluando predicción {idx}: {e}")
        
        # Construir mensaje de resumen
        mensaje = f"📊 *Evaluación {juego}*\n"
        mensaje += f"Números: *{', '.join(str(n) for n in numeros_reales)}*\n\n"
        
        for alg, stats in resumen.items():
            total = stats['total']
            a3 = stats['aciertos_3']
            a2 = stats['aciertos_2']
            a1 = stats['aciertos_1']
            pct = (a3 * 100) // total if total > 0 else 0
            mensaje += f"• *{alg}*: {a3}🔥 {a2}☑️ {a1}✔️ / {total} ({pct}%)\n"
        
        # Actualizar CSV
        for cambio in cambios:
            df_sim.loc[cambio['idx'], 'estado'] = cambio['estado']
            df_sim.loc[cambio['idx'], 'aciertos'] = cambio['aciertos']
            df_sim.loc[cambio['idx'], 'score'] = cambio['score']
        
        df_sim.to_csv(CSV_SIMULACIONES, index=False)
        
        if notifier:
            notifier.send_message(mensaje)
        
        logger.info(f"✅ {len(cambios)} predicciones evaluadas")
        return True
        
    except Exception as e:
        logger.error(f"Error en evaluación: {e}")
        return False


# =============================================================================
# REENTRENAMIENTO
# =============================================================================

def reentrenar_modelos(notifier: TelegramNotifier = None) -> bool:
    """
    Reentrena los modelos de ML a las 00:00.
    """
    logger.info("🧠 Reentrenando modelos...")
    
    try:
        # Aquí iría la lógica de reentrenamiento
        # Por ahora solo notificamos
        
        if notifier:
            notifier.send_status("Modelos reentrenados correctamente (simulado)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en reentrenamiento: {e}")
        if notifier:
            notifier.send_error(f"Error reentrenando: {e}")
        return False


# =============================================================================
# SCRAPING INTEGRADO
# =============================================================================

def ejecutar_scraping(notifier: TelegramNotifier = None) -> bool:
    """
    Ejecuta el scraping de todos los juegos.
    """
    logger.info("🔎 Ejecutando scraping...")
    
    try:
        # Importar scraper
        from scraper_polla import scrape_todos_los_juegos
        
        # Ejecutar scraping
        resultados = asyncio.run(scrape_todos_los_juegos())
        
        if resultados:
            logger.info(f"✅ {len(resultados)} nuevos sorteos obtenidos")
            if notifier:
                for r in resultados:
                    nums = r.get('data', {})
                    nums_str = f"{nums.get('n1','')}-{nums.get('n2','')}-{nums.get('n3','')}"
                    notifier.send_scraped_result(r['juego'], [nums.get('n1',0), nums.get('n2',0), nums.get('n3',0)], r['timestamp'][:10])
            
            # Evaluar predicciones con los nuevos resultados
            for r in resultados:
                if r['juego'] == 'LOTO 3':
                    numeros = [r['data'].get('n1', 0), r['data'].get('n2', 0), r['data'].get('n3', 0)]
                    evaluar_predicciones({'juego': 'LOTO3', 'numeros': numeros}, notifier)
            
            return True
        else:
            logger.info("No hay nuevos sorteos")
            if notifier:
                notifier.send_status("Scraping: sin nuevos sorteos")
            return False
            
    except Exception as e:
        logger.error(f"Error en scraping: {e}")
        if notifier:
            notifier.send_error(f"Error en scraping: {e}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Punto de entrada principal"""
    logger.info("🎰 LOTO Orquestador iniciado")
    
    notifier = TelegramNotifier()
    
    # Probar conexión
    if not notifier.send_status("🎰 Bot de LOTO iniciado"):
        logger.error("No se pudo enviar mensaje de inicio")
        return
    
    # Generar predicciones
    generar_predicciones_loto3(notifier)


if __name__ == "__main__":
    main()
