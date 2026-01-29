import pandas as pd
import ast
import numpy as np
import os
import json
import shutil

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
FILE_DASHBOARD = os.path.join(BASE_DIR, '..', '..', 'dashboard_data.json')

# Mapeo de archivos maestros (Añadimos referencia al Comodín para LOTO)
MAESTROS_CONFIG = {
    "LOTO":   {"file": "LOTO_HISTORIAL_MAESTRO.csv", "cols": ["LOTO_n1","LOTO_n2","LOTO_n3","LOTO_n4","LOTO_n5","LOTO_n6"], "comodin": "LOTO_comodin"},
    "LOTO3":  {"file": "LOTO3_MAESTRO.csv",          "cols": ["n1","n2","n3"], "orden_importa": True},
    "LOTO4":  {"file": "LOTO4_MAESTRO.csv",          "cols": ["n1","n2","n3","n4"]},
    "RACHA":  {"file": "RACHA_MAESTRO.csv",          "cols": ["n1","n2","n3","n4","n5","n6","n7","n8","n9","n10"]}
}

def cargar_maestros():
    """Carga todos los resultados históricos en un diccionario gigante en memoria."""
    memoria = {}
    
    for juego, config in MAESTROS_CONFIG.items():
        path = os.path.join(DATA_DIR, config['file'])
        if not os.path.exists(path):
            print(f"⚠️ No se encontró maestro para {juego}")
            continue
            
        try:
            df = pd.read_csv(path)
            mapa_sorteos = {}
            for _, row in df.iterrows():
                try:
                    # Extraer números ganadores
                    numeros = []
                    for col in config['cols']:
                        if col in row and not pd.isna(row[col]):
                            numeros.append(int(row[col]))

                    # --- NUEVO: Extraer Comodín si existe ---
                    comodin = None
                    if "comodin" in config and config["comodin"] in row:
                        val = row[config["comodin"]]
                        comodin = int(val) if not pd.isna(val) else None

                    if numeros:
                        sorteo_id = str(int(float(row['sorteo'])))
                        
                        # Determinar si ordenamos o no
                        lista_final = numeros if config.get("orden_importa") else sorted(numeros)
                        
                        # Ahora guardamos un diccionario con números y comodín
                        mapa_sorteos[sorteo_id] = {
                            "numeros": lista_final,
                            "comodin": comodin
                        }
                except (ValueError, TypeError, KeyError):
                    # Fila con datos malformados, saltar
                    continue
            
            memoria[juego] = mapa_sorteos
            print(f"📚 {juego}: {len(mapa_sorteos)} sorteos cargados en memoria.")
            
        except Exception as e:
            print(f"❌ Error cargando {juego}: {e}")
            
    return memoria

def calcular_afinidad(prediccion, realidad_obj, juego, modalidad=None):
    """
    Calcula score 0-100 dependiendo de las reglas del juego.

    Args:
        prediccion: Numeros predichos (lista o string para modalidades especiales)
        realidad_obj: Diccionario con {"numeros": [...], "comodin": X}
        juego: Nombre del juego (LOTO, LOTO3, LOTO4, RACHA)
        modalidad: Modalidad especial (PAR_INICIAL, PAR_FINAL, TERMINACION, o None para EXACTA)
    """
    if not prediccion or not realidad_obj: return 0.0

    # Extraemos los datos del objeto realidad
    realidad = realidad_obj["numeros"]
    comodin_real = realidad_obj.get("comodin")

    # === MODALIDADES ESPECIALES LOTO3 ===
    if modalidad == 'PAR_INICIAL' and juego == 'LOTO3':
        # Comparar par predicho con los primeros 2 digitos reales
        par_real = f"{realidad[0]}{realidad[1]}"
        prediccion_str = str(prediccion) if not isinstance(prediccion, str) else prediccion
        return 100.0 if prediccion_str == par_real else 0.0

    elif modalidad == 'PAR_FINAL' and juego == 'LOTO3':
        # Comparar par predicho con los ultimos 2 digitos reales
        par_real = f"{realidad[1]}{realidad[2]}"
        prediccion_str = str(prediccion) if not isinstance(prediccion, str) else prediccion
        return 100.0 if prediccion_str == par_real else 0.0

    elif modalidad == 'TERMINACION' and juego == 'LOTO3':
        # Comparar digito predicho con el ultimo digito real
        terminacion_real = realidad[2]
        try:
            pred_int = int(prediccion) if isinstance(prediccion, str) else prediccion
            return 100.0 if pred_int == terminacion_real else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    # --- REGLAS RACHA (Curva Monótona de Afinidad) ---
    if juego == "RACHA":
        aciertos = len(set(prediccion) & set(realidad))
        
        # FIX [IMP-AUD-001]: Eliminamos la "V invertida". 
        # La IA debe aprender a acertar, no a fallar intencionalmente.
        # Nueva escala lineal ponderada hacia el éxito:
        if aciertos >= 10: return 100.0  # Pleno
        if aciertos == 9: return 90.0
        if aciertos == 8: return 75.0
        if aciertos == 7: return 50.0
        if aciertos == 6: return 30.0
        if aciertos == 5: return 15.0
        if aciertos == 4: return 5.0
        
        # Menos de 4 aciertos es irrelevante para afinidad predictiva positiva
        return 0.0 

    # --- REGLAS LOTO 3 (Basada en Premios Polla) ---
    elif juego == "LOTO3":
        # 1. EXACTA (400x): Coincidencia exacta
        if prediccion == realidad:
            return 100.0
        
        # 2. TRIO (65x - 130x): Mismos números, distinto orden
        # Nota: Cubre Trío Par y Trío Azar
        if sorted(prediccion) == sorted(realidad):
            return 60.0
            
        # 3. PAR (20x): Primeros 2 o Últimos 2 en orden exacto
        # Par Inicial: [A, B, x] vs [A, B, y]
        par_ini = (prediccion[0] == realidad[0] and prediccion[1] == realidad[1])
        # Par Final: [x, A, B] vs [y, A, B]
        par_fin = (prediccion[1] == realidad[1] and prediccion[2] == realidad[2])
        
        if par_ini or par_fin:
            return 40.0
            
        # 4. TERMINACIÓN (4x): Último dígito exacto
        if prediccion[2] == realidad[2]:
            return 15.0
            
        # 5. COINCIDENCIAS "INÚTILES" (Score bajo < 10.0)
        # Se otorga un puntaje marginal para diferenciar el "casi" del "nada",
        # pero significativamente menor que cualquier premio real.
        score_residual = 0.0
        
        # Acierto posicional no premiado (ej: Solo el 1er dígito)
        if prediccion[0] == realidad[0]: score_residual += 3.0
        if prediccion[1] == realidad[1]: score_residual += 3.0
        
        # Aciertos numéricos fuera de posición (muy débiles)
        # Calculamos intersección simple
        r_temp = list(realidad)
        matches_num = 0
        for n in prediccion:
            if n in r_temp:
                matches_num += 1
                r_temp.remove(n)
        
        score_residual += matches_num * 1.0
        
        # Tope máximo para basura (nunca superar a la Terminación)
        return min(score_residual, 10.0)

    # --- REGLAS LOTO / LOTO 4 (Escala de Mérito Normalizada) ---
    else: 
        aciertos = len(set(prediccion) & set(realidad))
        
        # CASO ESPECIAL LOTO 4 (Normalizado a 100)
        if juego == "LOTO4":
            if aciertos == 4: return 100.0
            if aciertos == 3: return 50.0
            if aciertos == 2: return 20.0
            return 0.0

        # --- NUEVA ESCALA LOTO 41 (Basada en Categorías Reales) ---
        tiene_comodin = (comodin_real is not None) and (comodin_real in prediccion)
        
        if aciertos == 6: return 100.0                    # Loto (Jackpot)
        if aciertos == 5 and tiene_comodin: return 85.0     # Súper Quina
        if aciertos == 5: return 70.0                    # Quina
        if aciertos == 4 and tiene_comodin: return 55.0     # Súper Cuaterna
        if aciertos == 4: return 40.0                    # Cuaterna
        if aciertos == 3 and tiene_comodin: return 25.0     # Súper Terna
        if aciertos == 3: return 15.0                    # Terna
        if aciertos == 2 and tiene_comodin: return 10.0     # Súper Dupla
        
        # Pequeño mérito basal para orientar a la IA (máx 5%)
        return (aciertos / 6) * 5

def juzgar(target_games=None):
    print("⚖️ JUEZ MULTIVERSO EN SESIÓN...")
    
    if not os.path.exists(FILE_SIMULACIONES):
        print("No hay simulaciones para juzgar.")
        return

    # 1. Cargar Memoria
    maestros = cargar_maestros()
    
    # 2. Leer Jugadas
    df_sim = pd.read_csv(FILE_SIMULACIONES)
    
    if 'juego' not in df_sim.columns:
        df_sim['juego'] = 'LOTO'
    
    cambios = 0
    cambios_dashboard = 0

    # 2.1 Cargar Dashboard para Sincronización
    dashboard_data = []
    dashboard_map = {}
    if os.path.exists(FILE_DASHBOARD):
        try:
            with open(FILE_DASHBOARD, 'r', encoding='utf-8') as f:
                dashboard_data = json.load(f)
                # Crear mapa para acceso rápido por ID
                for item in dashboard_data:
                    if 'id' in item:
                        dashboard_map[int(item['id'])] = item
            print(f"📊 Dashboard cargado: {len(dashboard_data)} registros.")
        except Exception as e:
            print(f"⚠️ Error cargando dashboard: {e}")
    
    # 3. Iterar y Juzgar
    for index, row in df_sim.iterrows():
        juego = row['juego']
        
        # Filtrado optimizado: Si nos dieron target_games, ignoramos el resto
        if target_games is not None and juego not in target_games:
            continue

        try:
            target_id = str(int(float(row['sorteo_objetivo'])))
        except (ValueError, TypeError):
            # Fila con sorteo_objetivo malformado, saltar
            continue
        
        if juego in maestros and target_id in maestros[juego]:
            # Realidad ahora es un dict con {"numeros": [...], "comodin": X}
            realidad_obj = maestros[juego][target_id]
            nums_real = realidad_obj["numeros"]
            
            # Detectar modalidad especial (PAR_INICIAL, PAR_FINAL, TERMINACION)
            modalidad = row.get('modalidad', None) if 'modalidad' in df_sim.columns else None
            if pd.isna(modalidad):
                modalidad = None

            try:
                raw_nums = row['numeros']

                # Para modalidades especiales, los numeros pueden ser strings simples
                if modalidad in ['PAR_INICIAL', 'PAR_FINAL', 'TERMINACION']:
                    nums_pred = str(raw_nums).strip()
                elif isinstance(raw_nums, str):
                    # SEC-FIX: Usar json.loads en lugar de ast.literal_eval
                    # para evitar ejecución de código arbitrario.
                    try:
                        nums_pred = json.loads(raw_nums)
                    except json.JSONDecodeError:
                        # Fallback seguro solo si es estrictamente necesario,
                        # pero preferimos loggear el error.
                        # Intentamos limpiar formato python a json si es necesario
                        nums_pred = ast.literal_eval(raw_nums)
                else:
                    nums_pred = raw_nums

                # Para modalidades estandar, necesitamos lista
                if modalidad not in ['PAR_INICIAL', 'PAR_FINAL', 'TERMINACION']:
                    if not isinstance(nums_pred, list):
                        continue
            except (ValueError, SyntaxError, TypeError):
                # Números mal formateados, saltar predicción
                continue

            # Calcular Aciertos para display (Lógica original)
            if modalidad in ['PAR_INICIAL', 'PAR_FINAL']:
                # Para pares: 1 si acierta, 0 si no
                aciertos_display = 0  # Se actualizara con el score
            elif modalidad == 'TERMINACION':
                # Para terminacion: 1 si acierta, 0 si no
                aciertos_display = 0  # Se actualizara con el score
            elif juego == "LOTO3":
                 aciertos_display = 0
                 r_cp = list(nums_real)
                 for n in nums_pred:
                     if n in r_cp:
                         aciertos_display +=1
                         r_cp.remove(n)
            else:
                aciertos_display = len(set(nums_pred) & set(nums_real))

            # Score interno (NUEVA ESCALA con soporte de modalidad)
            score_final = calcular_afinidad(nums_pred, realidad_obj, juego, modalidad=modalidad)

            # Actualizar aciertos para modalidades especiales basado en score
            if modalidad in ['PAR_INICIAL', 'PAR_FINAL', 'TERMINACION']:
                aciertos_display = 1 if score_final == 100.0 else 0
            
            old_score = float(row['score_afinidad']) if not pd.isna(row['score_afinidad']) else -1.0
            
            # Actualizamos si cambió el score (importante para recalibrar el histórico)
            if row['estado'] != 'AUDITADO' or abs(score_final - old_score) > 0.01:
                df_sim.at[index, 'aciertos'] = aciertos_display
                df_sim.at[index, 'score_afinidad'] = round(score_final, 2)
                df_sim.at[index, 'estado'] = 'AUDITADO'
                cambios += 1
                
                # Sincronizar con Dashboard
                try:
                    if 'id' in row and not pd.isna(row['id']):
                        sim_id = int(row['id'])
                        if sim_id in dashboard_map:
                            dash_item = dashboard_map[sim_id]
                            
                            dash_score = float(dash_item.get('score_afinidad', 0))
                            
                            if (dash_item.get('estado') != 'AUDITADO' or 
                                abs(dash_score - score_final) > 0.01):
                                
                                dash_item['aciertos'] = int(aciertos_display)
                                dash_item['score_afinidad'] = round(score_final, 2)
                                dash_item['estado'] = 'AUDITADO'
                                cambios_dashboard += 1
                except Exception:
                    pass

                if cambios % 10 == 0:
                    print(f"    🔨 Sentencia dictada para {juego} #{target_id}. Score: {score_final:.1f}%")

    # 5. Guardar
    if cambios > 0:
        # [IMP-DATA-003] Backup preventivo antes de sobrescribir
        try:
            shutil.copy(FILE_SIMULACIONES, FILE_SIMULACIONES + ".bak")
        except Exception as e:
            print(f"⚠️ No se pudo crear backup: {e}")

        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✅ {cambios} veredictos actualizados y normalizados.")
    else:
        print("💤 La corte no encontró casos nuevos para juzgar.")

    # 6. Guardar Dashboard si hubo cambios
    if cambios_dashboard > 0:
        try:
            with open(FILE_DASHBOARD, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Dashboard sincronizado: {cambios_dashboard} registros actualizados.")
        except Exception as e:
            print(f"❌ Error guardando dashboard: {e}")

if __name__ == "__main__":
    juzgar()