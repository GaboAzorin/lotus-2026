import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
import sys
import csv

# --- GESTIÓN DE RUTAS ROBUSTA ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importamos sin miedo (Manejo de errores explícito)
try:
    import juez_implacable
    import entrenador_cognitivo
    try:
        from oraculo_neural import OraculoNeural
    except ImportError:
        OraculoNeural = None
        print("⚠️ Advertencia: OraculoNeural no encontrado. El Time Travel será limitado.")

except ImportError as e:
    print(f"❌ ERROR CRÍTICO EN RECONSTRUCTOR: No puedo importar mis dependencias.")
    raise e 

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

# Mapeo de archivos maestros
JUEGOS = {
    "LOTO3": "LOTO3_MAESTRO.csv",
    "RACHA": "RACHA_MAESTRO.csv",
    "LOTO":  "LOTO_HISTORIAL_MAESTRO.csv",
    "LOTO4": "LOTO4_MAESTRO.csv"
}

def formato_hms(segundos):
    """Convierte segundos en formato legible h:m:s"""
    return str(timedelta(seconds=int(segundos)))

def obtener_ultimo_procesado(juego):
    """Busca en el genoma hasta qué sorteo ya hemos 'viajado'."""
    if not os.path.exists(GENOMA_FILE):
        return 0
    try:
        with open(GENOMA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("last_processed", {}).get(juego, 0)
    except (json.JSONDecodeError, IOError):
        return 0

def actualizar_ultimo_procesado(juego, sorteo_id):
    """Guarda en el genoma que ya procesamos este hito temporal."""
    data = {}
    if os.path.exists(GENOMA_FILE):
        try:
            with open(GENOMA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}

    if "last_processed" not in data:
        data["last_processed"] = {}
    data["last_processed"][juego] = int(sorteo_id)

    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def reconstruir_linea_tiempo():
    print("⏳ INICIANDO RECONSTRUCCIÓN EXHAUSTIVA (MODO HOMOLOGACIÓN TOTAL)...")

    for juego, archivo in JUEGOS.items():
        path = os.path.join(DATA_DIR, archivo)
        if not os.path.exists(path): continue

        # 1. Leer historia real
        try:
            df_real = pd.read_csv(path)
        except (IOError, pd.errors.ParserError) as e:
            print(f"   Error leyendo {archivo}: {e}")
            continue

        if 'sorteo' not in df_real.columns: continue

        # Ordenar cronológicamente
        df_real = df_real.sort_values('sorteo', ascending=True).reset_index(drop=True)
        todos_sorteos = df_real['sorteo'].unique()

        # 2. Determinar punto de partida
        ultimo_procesado = obtener_ultimo_procesado(juego)
        nuevos = [s for s in todos_sorteos if s > ultimo_procesado]

        if not nuevos:
            continue

        total_a_procesar = len(nuevos)
        print(f"\n🚀 {juego}: Detectados {total_a_procesar} sorteos nuevos.")
        print(f"   📅 Sincronizando desde sorteo #{min(nuevos)}...")

        # --- ⏱️ CRONÓMETRO GLOBAL ---
        inicio_global = time.time()
        procesados_count = 0

        # 3. BUCLE DE VIAJE EN EL TIEMPO
        for i, sorteo_actual in enumerate(nuevos):
            # --- ⏱️ CRONÓMETRO INDIVIDUAL ---
            inicio_iteracion = time.time()

            # --- [BLOQUE VISUAL MEJORADO] ---
            if i > 0:
                print(f"   └── ✅ Ciclo completado. Preparando siguiente salto temporal...\n")

            print("═" * 70)
            print(f"📅  NUEVO HITO TEMPORAL DETECTADO")
            print(f"🎯  OBJETIVO: Sorteo Nº {sorteo_actual} ({juego})")
            print("═" * 70)

            # [A] CÁLCULO DE FECHA
            try:
                fila_actual = df_real[df_real['sorteo'] == sorteo_actual].iloc[0]
                fecha_target_str = str(fila_actual['fecha'])
                if 'T' in fecha_target_str:
                    fecha_target_dt = datetime.strptime(fecha_target_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                else:
                    fecha_target_dt = datetime.strptime(fecha_target_str, '%Y-%m-%d %H:%M:%S')
                fecha_simulada = fecha_target_dt - timedelta(hours=1)
            except: 
                fecha_target_dt = datetime.now(); fecha_simulada = datetime.now()

            # [B] JUEZ Y ENTRENADOR
            print(f"⚖️  JUEZ MULTIVERSO EN SESIÓN...", end=" ")
            juez_implacable.juzgar() 
            print("") 
            entrenador_cognitivo.analizar_adn_ganador()

            # [C] ORÁCULO (CAMBIO: COEXISTENCIA V3 y V4)
            if OraculoNeural:
                for v_name in ["v3", "v4"]:
                    algo_tag = f"oraculo_neural_{v_name}"
                    
                    # 1. Limpieza de duplicados para esta versión específica
                    if os.path.exists(SIMULACIONES_FILE):
                        try:
                            df_sim = pd.read_csv(SIMULACIONES_FILE, usecols=['juego', 'sorteo_objetivo', 'algoritmo'])
                            hay_duplicado = ((df_sim['juego'] == juego) &
                                             (df_sim['sorteo_objetivo'] == sorteo_actual) &
                                             (df_sim['algoritmo'] == algo_tag)).any()
                            if hay_duplicado:
                                df_full = pd.read_csv(SIMULACIONES_FILE)
                                mask = (df_full['juego'] == juego) & \
                                       (df_full['sorteo_objetivo'] == sorteo_actual) & \
                                       (df_full['algoritmo'] == algo_tag)
                                df_full = df_full[~mask]
                                df_full.to_csv(SIMULACIONES_FILE, index=False)
                        except (IOError, KeyError, pd.errors.ParserError):
                            # Error leyendo simulaciones, continuar sin limpiar
                            pass

                    # 2. Entrenamiento y Predicción
                    try:
                        # Instanciamos la versión correspondiente
                        oraculo_inst = OraculoNeural(juego, version=v_name)
                        oraculo_inst.entrenar(sorteo_limite=sorteo_actual -1)
                        prediccion = oraculo_inst.predecir(fecha_objetivo=fecha_target_dt)

                        if prediccion:
                            print(f"🔮 {v_name.upper()}: {prediccion}", end=" ") 

                            timestamp_simulado = int(time.time())
                            import random
                            id_ficticio = int(f"{timestamp_simulado}{random.randint(100,999)}")

                            nueva_fila = {
                                'id': id_ficticio,
                                'fecha_generacion': fecha_simulada.strftime('%Y-%m-%d %H:%M:%S'),
                                'juego': juego,
                                'numeros': str(sorted(prediccion)),
                                'sorteo_objetivo': sorteo_actual,
                                'estado': 'PENDIENTE', 
                                'aciertos': 0, 'score_afinidad': 0.0,
                                'hora_dia': fecha_simulada.hour,
                                'algoritmo': algo_tag
                            }

                            file_exists = os.path.exists(SIMULACIONES_FILE)
                            mode = 'a' if file_exists else 'w'
                            keys = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 
                                    'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']

                            with open(SIMULACIONES_FILE, mode, newline='', encoding='utf-8') as f:
                                w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                                if not file_exists: w.writeheader()
                                w.writerow(nueva_fila)

                    except Exception as e:
                        print(f"⚠️ Err {v_name}: {e}", end=" ")

            # [D] MARCAR HITO
            actualizar_ultimo_procesado(juego, sorteo_actual)

            # --- ⏱️ CÁLCULOS DE TELEMETRÍA ---
            fin_iteracion = time.time()
            tiempo_ciclo = fin_iteracion - inicio_iteracion

            procesados_count += 1
            tiempo_transcurrido = fin_iteracion - inicio_global
            velocidad_promedio = tiempo_transcurrido / procesados_count
            restantes = total_a_procesar - procesados_count
            eta_segundos = restantes * velocidad_promedio

            print(f"✅ [{tiempo_ciclo:.1f}s | T:{formato_hms(tiempo_transcurrido)} | Resta:{formato_hms(eta_segundos)}]")

    print("\n✨ RECONSTRUCCIÓN FINALIZADA.")

    try:
        try:
            import comparar_modelos
            comparar_modelos.generar_reporte_markdown()
        except ImportError:
            print("⚠️ No se encontró el script comparar_modelos en el path.")
        print("📝 Generando reporte comparativo v3 vs v4...")
        comparar_modelos.generar_reporte_markdown()
        print("✅ Reporte 'COMPARATIVA_MODELOS.md' actualizado.")
    except Exception as e:
        print(f"⚠️ No se pudo generar el reporte: {e}")

if __name__ == "__main__":
    reconstruir_linea_tiempo()