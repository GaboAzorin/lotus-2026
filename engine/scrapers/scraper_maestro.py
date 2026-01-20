import asyncio
import csv
import os
import json
import requests
import time
import re
import subprocess
import sys
import importlib
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ==============================================================================
# 1. CONFIGURACIÓN DE ENTORNO Y RUTAS
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')
TOOLS_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'tools'))
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

# Vital: Agregamos 'models' al path para poder invocar al cerebro luego
if MODELS_DIR not in sys.path:
    sys.path.append(MODELS_DIR)

# --- IMPORTACIÓN DE PARSERS ---
try:
    from loto_parser_v3 import parse_loto_rich
    from loto_parsers_mix import parse_loto3, parse_loto4, parse_racha
    PARSERS_DISPONIBLES = True
except ImportError as e:
    logger.warning(f"Parsers no encontrados: {e}. El scraper funcionará en modo limitado.")
    PARSERS_DISPONIBLES = False
    parse_loto_rich = parse_loto3 = parse_loto4 = parse_racha = None

# ==============================================================================
# 2. CONSTANTES Y CONFIGURACIÓN
# ==============================================================================

# URL de tu Google Sheet (CSV público para inyectar jugadas externas)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQnOXW1U2VkJdNw6DplTvNGb5R3Fc6yNPKuewnBqh9w9C01m9ht2N8dNi3C4oqvIyL6An-coGf0TjhR/pub?output=csv"
JUGADAS_CSV = os.path.join(DATA_DIR, "LOTO_JUGADAS.csv")

# Endpoints de Polla Chilena
API_URL = "https://www.polla.cl/es/get/draw/results"
BASE_URL = "https://www.polla.cl/es/view/resultados"

# --- AUDITORÍA v4: RATE LIMITING Y TOKEN REFRESH ---
REQUEST_DELAY_SECONDS = 0.5  # Delay entre requests para evitar bloqueo IP
TOKEN_REFRESH_MINUTES = 20   # Revalidar token CSRF cada 20 minutos
MAX_CONSECUTIVE_ERRORS = 5   # Máximo errores antes de detener

# Configuración Maestra (El Mapa del Multiverso)
GAME_CONFIG = [
    {
        "name": "LOTO", "id": "5271",
        "csv": os.path.join(DATA_DIR, "LOTO_HISTORIAL_MAESTRO.csv"),
        "parser": parse_loto_rich, "start_draw": 3803,
        "cols": [
            "sorteo", "fecha", "ventas_totales", "boletos_estimados",
            "LOTO_n1", "LOTO_n2", "LOTO_n3", "LOTO_n4", "LOTO_n5", "LOTO_n6", "LOTO_comodin",
            "LOTO_GANADORES", "LOTO_MONTO", "LOTO_POZO_REAL", "LOTO_POZO_ACUMULADO"
        ]
    },
    {
        "name": "LOTO 3", "id": "2181",
        "csv": os.path.join(DATA_DIR, "LOTO3_MAESTRO.csv"),
        "parser": parse_loto3, "start_draw": 12991,
        "cols": ["sorteo", "fecha", "dia_semana", "hora", "momento", "combinacion", "n1", "n2", "n3"]
    },
    {
        "name": "LOTO 4", "id": "5270",
        "csv": os.path.join(DATA_DIR, "LOTO4_MAESTRO.csv"),
        "parser": parse_loto4, "start_draw": 4230,
        "cols": ["sorteo", "fecha", "dia_semana", "hora", "n1", "n2", "n3", "n4", "pos1", "pos2", "pos3", "pos4"]
    },
    {
        "name": "RACHA", "id": "5272",
        "csv": os.path.join(DATA_DIR, "RACHA_MAESTRO.csv"),
        "parser": parse_racha, "start_draw": 2963,
        "cols": ["sorteo", "fecha", "dia_semana", "hora", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "n10"]
    }
]

# ==============================================================================
# 3. FUNCIONES AUXILIARES ROBUSTAS
# ==============================================================================

def sincronizar_jugadas():
    """Descarga jugadas manuales/externas desde Google Sheets y las fusiona sin duplicados."""
    print("\n☁️  Sincronizando jugadas desde la nube (Google Sheets)...")
    try:
        # Timeout aumentado para conexiones inestables
        response = requests.get(GOOGLE_SHEET_CSV_URL, timeout=30)
        if response.status_code != 200:
            logger.warning(f"Google Sheets respondió con código {response.status_code}. Saltando sincronización.")
            print("   ⚠️ No se pudo conectar a Sheets. Saltando sincronización.")
            return

        # Validar que la respuesta contiene datos CSV válidos
        content_type = response.headers.get('content-type', '')
        if 'text/csv' not in content_type and 'text/plain' not in content_type:
            logger.warning(f"Google Sheets devolvió tipo inesperado: {content_type}. El documento puede estar privado o eliminado.")
            print("   ⚠️ El documento Google Sheets parece estar privado o no disponible.")
            return

        if len(response.text.strip()) < 10:
            logger.warning("Google Sheets devolvió respuesta vacía o muy corta.")
            print("   ⚠️ El documento Google Sheets parece vacío.")
            return

        # 1. Cargar huellas digitales existentes (Fecha + Números) para evitar duplicados
        jugadas_existentes = set()
        
        if os.path.exists(JUGADAS_CSV):
            with open(JUGADAS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, []) # Saltar header
                for row in reader:
                    if len(row) > 2:
                        # Normalización agresiva para comparación
                        fecha_clean = row[1].strip()
                        nums_clean = row[2].replace(" ", "") 
                        key = f"{fecha_clean}|{nums_clean}"
                        jugadas_existentes.add(key)

        filas_nube = list(csv.reader(response.text.splitlines()))
        if not filas_nube: return

        # Detectar inicio de datos (saltar headers de la sheet)
        start_idx = 1 if len(filas_nube) > 0 and "fecha" in filas_nube[0][0].lower() else 0
        
        nuevas = 0
        modos_append = 'a' if os.path.exists(JUGADAS_CSV) else 'w'
        
        # Estructura COMPLETA requerida
        HEADERS_NUEVOS = ["id", "fecha_generacion", "numeros", "jugado_realmente", "estado", "sorteo_objetivo", "juego"]

        with open(JUGADAS_CSV, modos_append, encoding='utf-8', newline='') as f:
            # extrasaction='ignore' permite que si la sheet tiene columnas basura, no explote
            writer = csv.DictWriter(f, fieldnames=HEADERS_NUEVOS, extrasaction='ignore')
            if modos_append == 'w': writer.writeheader()

            for i in range(start_idx, len(filas_nube)):
                try:
                    fila = filas_nube[i]
                    if len(fila) < 3: continue
                    
                    # Formato Google Sheet: Fecha ISO, 1-2-3, SI/NO
                    fecha_raw = fila[0].replace("T", " ").replace("Z", "").split(".")[0]
                    nums_str = fila[1]
                    jugado = fila[2]

                    # Convertir a JSON array estandarizado
                    try:
                        lista_nums = [int(n) for n in nums_str.split('-')]
                        nums_json = json.dumps(lista_nums)
                    except (ValueError, AttributeError):
                        # Números mal formateados, saltar fila
                        continue

                    # Check de duplicado
                    key_check = f"{fecha_raw}|{nums_json.replace(' ', '')}"
                    if key_check in jugadas_existentes: continue 
                    
                    # Crear fila estandarizada
                    row_data = {
                        "id": int(time.time()) + nuevas,
                        "fecha_generacion": fecha_raw,
                        "numeros": nums_json,
                        "jugado_realmente": jugado,
                        "estado": "PENDIENTE",
                        "juego": "LOTO", # Asumimos Loto por defecto si viene de esta sheet
                        "sorteo_objetivo": ""
                    }
                    writer.writerow(row_data)
                    nuevas += 1
                    print(f"   ✨ Nueva jugada importada: {fecha_raw}")
                    
                except Exception as e: 
                    # Error puntual en una fila no detiene el proceso
                    continue
        
        if nuevas > 0: print(f"   📥 {nuevas} jugadas nuevas agregadas.")
        else: print("   ✅ Sincronización al día (0 duplicados).")

    except Exception as e:
        print(f"   ❌ Error crítico en sync nube: {e}")

def get_start_id(config):
    """Obtiene el último ID sorteado leyendo el CSV local."""
    if not os.path.exists(config['csv']):
        return config['start_draw']
    max_id = 0
    try:
        with open(config['csv'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('sorteo') and row['sorteo'].isdigit():
                    sid = int(row['sorteo'])
                    if sid > max_id:
                        max_id = sid
    except (IOError, csv.Error) as e:
        logger.warning(f"Error leyendo CSV {config['csv']}: {e}")
    return max_id + 1 if max_id > 0 else config['start_draw']

def subir_cambios_a_github():
    print("\n📦 SUBIENDO DATOS A GITHUB...")
    try:
        # Verificar si hay cambios reales antes de spammear commits
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
        if not status:
            print("   ✅ No hay datos nuevos para subir.")
            return

        subprocess.run(["git", "add", "."], check=True)
        
        mensaje = f"🤖 Update local: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", mensaje], check=True)
        
        subprocess.run(["git", "push"], check=True)
        print("   🚀 ¡Listo! Los datos ya están en la web.")
        
    except Exception as e:
        print(f"   ⚠️ No se pudo subir a GitHub (¿Sin internet?): {e}")

def bloquear_sonador():
    """Deshabilita el workflow 'soñador.yml' en GitHub para evitar conflictos."""
    print("\n🔒 Bloqueando Soñador en GitHub (evitando conflictos)...")
    try:
        # Usamos gh cli. Asumimos que está instalado y autenticado.
        subprocess.run(["gh", "workflow", "disable", "soñador.yml"], check=True, capture_output=True)
        print("   ✅ Soñador pausado correctamente.")
    except Exception as e:
        print(f"   ⚠️ No se pudo bloquear Soñador (¿gh cli instalado?): {e}")

def desbloquear_sonador():
    """Habilita nuevamente el workflow 'soñador.yml' en GitHub."""
    print("\n🔓 Desbloqueando Soñador en GitHub...")
    try:
        subprocess.run(["gh", "workflow", "enable", "soñador.yml"], check=True, capture_output=True)
        print("   ✅ Soñador reactivado. Listo para soñar.")
    except Exception as e:
        print(f"   ⚠️ No se pudo desbloquear Soñador: {e}")

# ==============================================================================
# 4. MOTOR PRINCIPAL (SCRAPER)
# ==============================================================================

async def obtener_token_csrf(page):
    """
    Obtiene token CSRF de Polla.cl.
    AUDITORÍA v4: Función separada para permitir revalidación.
    """
    logger.info("Obteniendo token de sesión Polla.cl...")
    await page.goto(BASE_URL, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # Intento A: Vía DOM (Input hidden)
    token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")

    # Intento B: Vía Regex (Si el DOM está ofuscado)
    if not token:
        logger.warning("Token no encontrado en DOM. Intentando extracción profunda...")
        content = await page.content()
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
        if m:
            token = m.group(1)
            logger.info("Token recuperado vía Regex.")

    if not token:
        raise Exception("No se encontró token CSRF por ningún método.")

    logger.info("Token validado.")
    return token


async def _run_scraper_internal():
    logger.info("INICIANDO SCRAPER MAESTRO (Modo Manual/Local)...")
    sincronizar_jugadas()

    async with async_playwright() as p:
        # Lanzamos navegador headless pero con stealth basics
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # --- A. OBTENCIÓN DE TOKEN CON TIMESTAMP ---
        try:
            token = await obtener_token_csrf(page)
            token_timestamp = datetime.now()
        except Exception as e:
            logger.error(f"Error fatal conectando a Polla.cl: {e}")
            await browser.close()
            return

        # --- B. BUCLE DE JUEGOS ---
        for game in GAME_CONFIG:
            current_id = get_start_id(game)
            logger.info(f"{game['name']} (ID {game['id']}) | Buscando desde #{current_id}")
            consecutive_errors = 0

            # Umbral de errores consecutivos para detener (evita bucles infinitos)
            while consecutive_errors < MAX_CONSECUTIVE_ERRORS:
                try:
                    # AUDITORÍA v4: Revalidar token si ha expirado
                    if datetime.now() - token_timestamp > timedelta(minutes=TOKEN_REFRESH_MINUTES):
                        logger.info("Token CSRF expirado. Revalidando...")
                        try:
                            token = await obtener_token_csrf(page)
                            token_timestamp = datetime.now()
                        except Exception as e:
                            logger.error(f"Error revalidando token: {e}")
                            break

                    # AUDITORÍA v4: Rate limiting
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)

                    # Petición AJAX emulada
                    response = await page.request.post(API_URL, data={
                        "gameId": game['id'], "drawId": current_id, "csrfToken": token
                    }, headers={"x-requested-with": "XMLHttpRequest"})

                    if response.status == 200:
                        try:
                            json_data = await response.json()
                        except json.JSONDecodeError:
                            logger.warning("Respuesta recibida pero JSON inválido.")
                            consecutive_errors += 1
                            continue

                        # Validación 1: ¿Viene vacío o sin resultados?
                        if not json_data or not json_data.get('results'):
                            # Puede ser un sorteo futuro o un salto de folio
                            ts = json_data.get('drawDate')
                            if ts and datetime.fromtimestamp(ts/1000) > datetime.now():
                                logger.info(f"Sorteo #{current_id} es futuro. Deteniendo {game['name']}.")
                                break  # Salimos del bucle de este juego

                            # Si no es futuro, quizás es un ID vacío, probamos el siguiente
                            current_id += 1
                            consecutive_errors += 1
                            continue

                        # Validación 2: Parseo
                        try:
                            row = game['parser'](json_data)
                        except Exception as parse_err:
                            logger.warning(f"Error parseando datos #{current_id}: {parse_err}")
                            consecutive_errors += 1
                            continue

                        # --- GUARDADO INTELIGENTE (HEADER DINÁMICO) ---
                        file_exists = os.path.exists(game['csv'])
                        fieldnames = list(game['cols'])

                        # Si el parser trajo columnas nuevas (ej: Jubilazo nuevo), las agregamos
                        for k in row.keys():
                            if k not in fieldnames:
                                fieldnames.append(k)

                        existing_headers = []
                        if file_exists:
                            with open(game['csv'], 'r', encoding='utf-8') as f:
                                # Leemos headers actuales del archivo
                                reader = csv.DictReader(f)
                                existing_headers = reader.fieldnames or []

                            # Fusionamos headers viejos con nuevos
                            final_headers = existing_headers
                            for k in row.keys():
                                if k not in final_headers:
                                    final_headers.append(k)
                        else:
                            final_headers = fieldnames

                        with open(game['csv'], 'a', encoding='utf-8', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=final_headers)
                            # Si es archivo nuevo, escribir header
                            if not file_exists:
                                writer.writeheader()
                            writer.writerow(row)

                        logger.info(f"#{row['sorteo']} Guardado OK")
                        current_id += 1
                        consecutive_errors = 0  # Reset racha errores
                    else:
                        logger.warning(f"Error HTTP {response.status}")
                        consecutive_errors += 1
                        await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Excepción en ciclo: {e}")
                    consecutive_errors += 1
                    await asyncio.sleep(1)

        await browser.close()
        
        # ==============================================================================
        # 5. PIPELINE DE INTELIGENCIA ARTIFICIAL COMPLETO
        # ==============================================================================
        # Ejecuta el ciclo completo de auto-mejora:
        # 1. Juez Implacable → Audita predicciones vs resultados reales
        # 2. Entrenador Cognitivo → Actualiza genoma con aprendizaje incremental
        # 3. Generador Biométrico → Recalcula frecuencias con suavizado Laplace
        # 4. Auto-Optimizer → Detecta drift, promueve/degrada algoritmos
        # 5. Consolidar Laboratorio → Actualiza dashboard

        print("\n" + "="*60)
        print("🧠 PIPELINE DE INTELIGENCIA ARTIFICIAL v2.0")
        print("="*60)

        # --- PASO 1: JUEZ IMPLACABLE (Auditoría) ---
        print("\n⚖️  PASO 1/5: JUEZ IMPLACABLE (Auditando predicciones)...")
        try:
            from juez_implacable import juzgar
            importlib.reload(sys.modules.get('juez_implacable', sys.modules[__name__]))
            juzgar()
            print("   ✅ Auditoría completada.")
        except ImportError:
            print("   ⚠️ juez_implacable.py no encontrado. Saltando auditoría.")
        except Exception as e:
            print(f"   ❌ Error en auditoría: {e}")

        # --- PASO 2: ENTRENADOR COGNITIVO (Aprendizaje Incremental) ---
        print("\n🧬 PASO 2/5: ENTRENADOR COGNITIVO (Aprendiendo de resultados)...")
        try:
            from entrenador_cognitivo import analizar_adn_ganador
            importlib.reload(sys.modules.get('entrenador_cognitivo', sys.modules[__name__]))
            analizar_adn_ganador()
            print("   ✅ Genoma actualizado.")
        except ImportError:
            print("   ⚠️ entrenador_cognitivo.py no encontrado. Saltando entrenamiento.")
        except Exception as e:
            print(f"   ❌ Error en entrenamiento: {e}")

        # --- PASO 3: GENERADOR BIOMÉTRICO (Frecuencias + Laplace) ---
        print("\n📊 PASO 3/5: GENERADOR BIOMÉTRICO (Recalculando frecuencias)...")
        try:
            from generador_biometrico import generar_biometria
            importlib.reload(sys.modules.get('generador_biometrico', sys.modules[__name__]))
            generar_biometria()
            print("   ✅ Biometría actualizada con suavizado Laplace.")
        except ImportError:
            print("   ⚠️ generador_biometrico.py no encontrado. Saltando biometría.")
        except Exception as e:
            print(f"   ❌ Error en biometría: {e}")

        # --- PASO 4: AUTO-OPTIMIZER (Mejora Continua) ---
        print("\n🔄 PASO 4/5: AUTO-OPTIMIZER (Optimización automática)...")
        try:
            from auto_optimizer import ejecutar_optimizacion
            importlib.reload(sys.modules.get('auto_optimizer', sys.modules[__name__]))
            ejecutar_optimizacion()
            print("   ✅ Optimización completada.")
        except ImportError:
            print("   ⚠️ auto_optimizer.py no encontrado. Saltando optimización.")
        except Exception as e:
            print(f"   ❌ Error en optimización: {e}")

        # --- PASO 5: REENTRENAMIENTO PROFUNDO (Modelos .pkl) ---
        print("\n🧠 PASO 5/6: REENTRENAMIENTO PROFUNDO (Actualizando redes neuronales)...")
        try:
            from reentrenar_todo import reentrenar_modelos_profundos
            importlib.reload(sys.modules.get('reentrenar_todo', sys.modules[__name__]))
            reentrenar_modelos_profundos()
            print("   ✅ Modelos reentrenados.")
        except ImportError:
            print("   ⚠️ reentrenar_todo.py no encontrado. Saltando reentrenamiento.")
        except Exception as e:
            print(f"   ❌ Error en reentrenamiento: {e}")

        # --- PASO 6: CONSOLIDAR LABORATORIO (Dashboard) ---
        print("\n📈 PASO 6/6: CONSOLIDAR LABORATORIO (Actualizando dashboard)...")
        try:
            from consolidar_laboratorio import ejecutar_consolidacion_hibrida
            importlib.reload(sys.modules.get('consolidar_laboratorio', sys.modules[__name__]))
            ejecutar_consolidacion_hibrida()
            print("   ✅ Dashboard actualizado.")
        except ImportError:
            print("   ⚠️ consolidar_laboratorio.py no encontrado. Saltando consolidación.")
        except Exception as e:
            print(f"   ❌ Error en consolidación: {e}")

        print("\n" + "="*60)
        print("✨ PIPELINE COMPLETO - Sistema actualizado y optimizado")
        print("="*60)

        # ==============================================================================

        # Finalmente, subimos todo a la nube
        subir_cambios_a_github()

async def run_scraper():
    """Wrapper que maneja el bloqueo/desbloqueo de GitHub Actions."""
    bloquear_sonador()
    try:
        await _run_scraper_internal()
    finally:
        desbloquear_sonador()

if __name__ == "__main__":
    asyncio.run(run_scraper())