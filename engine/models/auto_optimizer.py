"""
AUTO-OPTIMIZER v1.0 - Sistema de Auto-Mejora Continua

Este módulo implementa un sistema de optimización automática que:
1. Monitorea el rendimiento de algoritmos en tiempo real
2. Detecta concept drift (cambios en la distribución)
3. Ajusta hiperparámetros automáticamente
4. Propone promoción/degradación de algoritmos
5. Genera reportes de salud del sistema

Ejecutar periódicamente (ej: después de cada auditoría).
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import logging

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")
OPTIMIZER_LOG = os.path.join(DATA_DIR, "optimizer_history.json")

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Umbrales de decisión
UMBRAL_DEGRADACION = 0.3      # Si score < 30% del promedio, degradar
UMBRAL_PROMOCION = 1.5        # Si score > 150% del promedio, promover
UMBRAL_DRIFT = 2.0            # Z-score para detectar concept drift
VENTANA_DRIFT = 50            # Últimas N predicciones para detectar drift
MIN_SAMPLES_DECISION = 20    # Mínimo de muestras para tomar decisiones


class AutoOptimizer:
    """Motor de auto-optimización del sistema de predicciones."""

    def __init__(self):
        self.genoma = self._cargar_genoma()
        self.historial = self._cargar_historial()
        self.recomendaciones = []

    def _cargar_genoma(self):
        if os.path.exists(GENOMA_FILE):
            with open(GENOMA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _cargar_historial(self):
        if os.path.exists(OPTIMIZER_LOG):
            with open(OPTIMIZER_LOG, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"optimizations": [], "drift_alerts": [], "health_checks": []}

    def _guardar_historial(self):
        with open(OPTIMIZER_LOG, 'w', encoding='utf-8') as f:
            json.dump(self.historial, f, indent=2, ensure_ascii=False)

    def ejecutar_ciclo_completo(self, target_games=None):
        """Ejecuta un ciclo completo de optimización."""
        print("\n" + "="*60)
        print("🔄 AUTO-OPTIMIZER v1.0: INICIANDO CICLO DE MEJORA CONTINUA")
        print("="*60)

        if not os.path.exists(SIMULACIONES_FILE):
            print("   ❌ No existe archivo de simulaciones.")
            return

        df = pd.read_csv(SIMULACIONES_FILE)
        df_audit = df[df['estado'] == 'AUDITADO'].copy()

        # Filtrar solo juegos objetivo si se especifican
        if target_games is not None:
            print(f"   🎯 Optimizando solo: {target_games}")
            df_audit = df_audit[df_audit['juego'].isin(target_games)]

        if len(df_audit) < MIN_SAMPLES_DECISION:
            print(f"   ⏳ Insuficientes muestras ({len(df_audit)} < {MIN_SAMPLES_DECISION}). Esperando más datos...")
            return

        # 1. Análisis de rendimiento por algoritmo
        self._analizar_rendimiento(df_audit)

        # 2. Detección de concept drift
        self._detectar_concept_drift(df_audit)

        # 3. Análisis de salud del sistema
        self._analisis_salud(df_audit)

        # 4. Generar y aplicar recomendaciones
        self._aplicar_recomendaciones()

        # 5. Guardar historial
        self._guardar_historial()

        print("\n✅ Ciclo de optimización completado.")

    def _analizar_rendimiento(self, df):
        """Analiza el rendimiento de cada algoritmo y detecta outliers."""
        print("\n📊 ANÁLISIS DE RENDIMIENTO:")

        for juego in df['juego'].unique():
            df_juego = df[df['juego'] == juego]
            if len(df_juego) < MIN_SAMPLES_DECISION:
                continue

            # Calcular métricas por algoritmo
            stats = df_juego.groupby('algoritmo').agg({
                'aciertos': ['mean', 'std', 'count'],
                'score_afinidad': ['mean', 'std']
            }).round(3)

            stats.columns = ['aciertos_mean', 'aciertos_std', 'count',
                           'score_mean', 'score_std']

            # Promedio global para comparar
            promedio_global = stats['aciertos_mean'].mean()

            print(f"\n   🎮 {juego}:")
            for algo, row in stats.iterrows():
                ratio = row['aciertos_mean'] / promedio_global if promedio_global > 0 else 1.0

                # Detectar algoritmos problemáticos
                if ratio < UMBRAL_DEGRADACION and row['count'] >= MIN_SAMPLES_DECISION:
                    self.recomendaciones.append({
                        'tipo': 'DEGRADAR',
                        'juego': juego,
                        'algoritmo': algo,
                        'razon': f"Rendimiento {ratio:.1%} del promedio",
                        'metrica': row['aciertos_mean']
                    })
                    estado = "🔻 BAJO"
                elif ratio > UMBRAL_PROMOCION and row['count'] >= MIN_SAMPLES_DECISION:
                    self.recomendaciones.append({
                        'tipo': 'PROMOVER',
                        'juego': juego,
                        'algoritmo': algo,
                        'razon': f"Rendimiento {ratio:.1%} del promedio",
                        'metrica': row['aciertos_mean']
                    })
                    estado = "🔺 ALTO"
                else:
                    estado = "✓ NORMAL"

                print(f"      {algo}: {row['aciertos_mean']:.2f} aciertos (n={int(row['count'])}) {estado}")

    def _detectar_concept_drift(self, df):
        """Detecta cambios en la distribución de resultados (concept drift)."""
        print("\n🌊 DETECCIÓN DE CONCEPT DRIFT:")

        for juego in df['juego'].unique():
            df_juego = df[df['juego'] == juego].sort_values('id')

            if len(df_juego) < VENTANA_DRIFT * 2:
                continue

            # Comparar últimas N predicciones vs históricas
            recientes = df_juego.tail(VENTANA_DRIFT)['aciertos'].values
            historicas = df_juego.head(len(df_juego) - VENTANA_DRIFT)['aciertos'].values

            # T-test aproximado (z-score de la diferencia de medias)
            mean_rec = np.mean(recientes)
            mean_hist = np.mean(historicas)
            std_hist = np.std(historicas) if np.std(historicas) > 0 else 1

            z_score = (mean_rec - mean_hist) / (std_hist / np.sqrt(VENTANA_DRIFT))

            if abs(z_score) > UMBRAL_DRIFT:
                direccion = "mejorando" if z_score > 0 else "empeorando"
                self.historial["drift_alerts"].append({
                    "timestamp": datetime.now().isoformat(),
                    "juego": juego,
                    "z_score": round(z_score, 2),
                    "mean_reciente": round(mean_rec, 3),
                    "mean_historico": round(mean_hist, 3)
                })
                print(f"   ⚠️ {juego}: DRIFT DETECTADO (z={z_score:.2f}) - Sistema {direccion}")

                self.recomendaciones.append({
                    'tipo': 'REENTRENAR',
                    'juego': juego,
                    'algoritmo': 'TODOS',
                    'razon': f"Concept drift detectado (z={z_score:.2f})",
                    'metrica': z_score
                })
            else:
                print(f"   ✓ {juego}: Sin drift significativo (z={z_score:.2f})")

    def _analisis_salud(self, df):
        """Análisis general de salud del sistema."""
        print("\n🏥 ANÁLISIS DE SALUD DEL SISTEMA:")

        salud = {
            "timestamp": datetime.now().isoformat(),
            "total_predicciones": len(df),
            "juegos_activos": list(df['juego'].unique()),
            "algoritmos_activos": list(df['algoritmo'].unique()),
            "metricas": {}
        }

        # Métricas globales
        for juego in df['juego'].unique():
            df_juego = df[df['juego'] == juego]
            salud["metricas"][juego] = {
                "promedio_aciertos": round(df_juego['aciertos'].mean(), 3),
                "max_aciertos": int(df_juego['aciertos'].max()),
                "tasa_exito_3plus": round((df_juego['aciertos'] >= 3).mean() * 100, 2),
                "n_predicciones": len(df_juego)
            }
            print(f"   {juego}: avg={salud['metricas'][juego]['promedio_aciertos']}, "
                  f"max={salud['metricas'][juego]['max_aciertos']}, "
                  f"tasa_3+={salud['metricas'][juego]['tasa_exito_3plus']}%")

        self.historial["health_checks"].append(salud)

        # Mantener solo los últimos 100 health checks
        if len(self.historial["health_checks"]) > 100:
            self.historial["health_checks"] = self.historial["health_checks"][-100:]

    def _aplicar_recomendaciones(self):
        """Aplica las recomendaciones automáticamente o las reporta."""
        if not self.recomendaciones:
            print("\n✨ Sin recomendaciones de optimización necesarias.")
            return

        print(f"\n📋 RECOMENDACIONES ({len(self.recomendaciones)}):")

        for rec in self.recomendaciones:
            emoji = {"DEGRADAR": "🔻", "PROMOVER": "🔺", "REENTRENAR": "🔄"}.get(rec['tipo'], "📌")
            print(f"   {emoji} {rec['tipo']}: {rec['juego']}/{rec['algoritmo']} - {rec['razon']}")

            # Registrar en historial
            self.historial["optimizations"].append({
                "timestamp": datetime.now().isoformat(),
                **rec
            })

        # Aplicar ajustes automáticos al genoma
        self._ajustar_genoma()

        # Mantener solo las últimas 200 optimizaciones
        if len(self.historial["optimizations"]) > 200:
            self.historial["optimizations"] = self.historial["optimizations"][-200:]

    def _ajustar_genoma(self):
        """Aplica ajustes automáticos al genoma basados en recomendaciones."""
        if not self.genoma.get("algo_ranking"):
            return

        cambios = 0
        for rec in self.recomendaciones:
            if rec['tipo'] == 'DEGRADAR' and rec['juego'] in self.genoma["algo_ranking"]:
                ranking = self.genoma["algo_ranking"][rec['juego']]
                if rec['algoritmo'] in ranking:
                    # Reducir peso en 20%
                    valor_actual = ranking[rec['algoritmo']]
                    ranking[rec['algoritmo']] = round(valor_actual * 0.8, 2)
                    cambios += 1
                    logger.info(f"Degradado {rec['algoritmo']} en {rec['juego']}: {valor_actual} → {ranking[rec['algoritmo']]}")

            elif rec['tipo'] == 'PROMOVER' and rec['juego'] in self.genoma["algo_ranking"]:
                ranking = self.genoma["algo_ranking"][rec['juego']]
                if rec['algoritmo'] in ranking:
                    # Aumentar peso en 15%
                    valor_actual = ranking[rec['algoritmo']]
                    ranking[rec['algoritmo']] = round(valor_actual * 1.15, 2)
                    cambios += 1
                    logger.info(f"Promovido {rec['algoritmo']} en {rec['juego']}: {valor_actual} → {ranking[rec['algoritmo']]}")

        if cambios > 0:
            # Guardar genoma actualizado
            self.genoma["metadata"]["last_optimization"] = datetime.now().isoformat()
            self.genoma["metadata"]["optimization_changes"] = cambios
            with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.genoma, f, indent=2, ensure_ascii=False)
            print(f"\n   💾 Genoma actualizado con {cambios} ajustes automáticos.")


def ejecutar_optimizacion(target_games=None):
    """Función principal para ejecutar desde línea de comandos o cron."""
    optimizer = AutoOptimizer()
    optimizer.ejecutar_ciclo_completo(target_games=target_games)


if __name__ == "__main__":
    ejecutar_optimizacion()
