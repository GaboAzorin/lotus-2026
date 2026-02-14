"""
Scraper para Polla.cl usando Playwright directo
Sin interfaz - solo obtener resultados y guardarlos

Versión corregida para manejar la API de Polla correctamente
"""
import os
import sys
import asyncio
import csv
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd
from playwright.async_api import async_playwright

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
SCRAPERS_DIR = os.path.join(CURRENT_DIR, 'scrapers')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importar parsers existentes
sys.path.insert(0, SCRAPERS_DIR)
try:
    from loto_parsers_mix import parse_loto3, parse_loto4, parse_racha
    from loto_parser_v3 import parse_loto_rich
    PARSERS_OK = True
except ImportError as e:
    logger.warning(f"Parsers no encontrados: {e}")
    PARSERS_OK = False

# Configuración
API_URL = "https://www.polla.cl/es/get/draw/results"
BASE_URL = "https://www.polla.cl/es/view/resultados"
REQUEST_DELAY = 0.5
TOKEN_REFRESH_MINUTES = 20
MAX_CONSECUTIVE_ERRORS = 5

# Juegos - con start_draw correcto
GAME_CONFIG = [
    {"name": "LOTO", "id": "5271", "csv": os.path.join(DATA_DIR, "LOTO_HISTORIAL_MAESTRO.csv"), "start_draw": 3803},
    {"name": "LOTO 3", "id": "2181", "csv": os.path.join(DATA_DIR, "LOTO3_MAESTRO.csv"), "start_draw": 12991},
    {"name": "LOTO 4", "id": "5270", "csv": os.path.join(DATA_DIR, "LOTO4_MAESTRO.csv"), "start_draw": 4230},
    {"name": "RACHA", "id": "5272", "csv": os.path.join(DATA_DIR, "RACHA_MAESTRO.csv"), "start_draw": 2963},
]


async def obtener_token(page) -> str:
    """Obtiene token CSRF de Polla.cl"""
    await page.goto(BASE_URL, wait_until="domcontentloaded")
    await asyncio.sleep(5)
    
    content = await page.content()
    m = re.search(r'"csrfToken":"([a-zA-Z0-9]+)"', content)
    if m:
        return m.group(1)
    
    m2 = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
    if m2:
        return m2.group(1)
    
    raise Exception("No se encontró CSRF Token")


def get_start_id(csv_path: str, start_draw: int) -> int:
    """Obtiene el último ID sorteado"""
    if not os.path.exists(csv_path):
        return start_draw
    
    try:
        df = pd.read_csv(csv_path)
        if 'sorteo' in df.columns:
            max_id = int(df['sorteo'].max())
            logger.info(f"  Ultimo ID en CSV: {max_id}")
            return max_id + 1
    except Exception as e:
        logger.warning(f"  Error leyendo CSV: {e}")
    return start_draw


async def scrape_juego(game: Dict) -> Optional[Dict]:
    """Scrapea un juego específico"""
    logger.info(f"[OK] Scraping {game['name']}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            token = await obtener_token(page)
            token_timestamp = datetime.now()
            
            current_id = get_start_id(game['csv'], game['start_draw'])
            logger.info(f"  Buscando desde ID #{current_id}")
            
            consecutive_errors = 0
            nuevos = 0
            
            while consecutive_errors < MAX_CONSECUTIVE_ERRORS:
                # Revalidar token
                if datetime.now() - token_timestamp > timedelta(minutes=TOKEN_REFRESH_MINUTES):
                    token = await obtener_token(page)
                    token_timestamp = datetime.now()
                
                await asyncio.sleep(REQUEST_DELAY)
                
                try:
                    response = await page.request.post(
                        API_URL,
                        data={"gameId": game['id'], "drawId": str(current_id), "csrfToken": token},
                        headers={"x-requested-with": "XMLHttpRequest", "Origin": "https://www.polla.cl"}
                    )
                    
                    if response.status == 200:
                        json_data = await response.json()
                        
                        # Verificar si hay resultados
                        results = json_data.get('results')
                        
                        if not results:
                            # Verificar si es futuro
                            ts = json_data.get('drawDate')
                            if ts:
                                fecha_sorteo = datetime.fromtimestamp(ts / 1000)
                                if fecha_sorteo > datetime.now():
                                    logger.info(f"  {game['name']}: Sorteo #{current_id} es futuro ({fecha_sorteo}). Deteniendo.")
                                    break
                            
                            # No hay resultados y no es futuro - siguiente ID
                            current_id += 1
                            consecutive_errors += 1
                            continue
                        
                        # Hay resultados - procesar
                        logger.info(f"  [OK] {game['name']} #{current_id}: {results}")
                        
                        # Guardar en CSV
                        guardar_resultado(game, current_id, json_data)
                        nuevos += 1
                        
                        # Reset errores y siguiente ID
                        consecutive_errors = 0
                        current_id += 1
                        
                    else:
                        consecutive_errors += 1
                        current_id += 1
                        
                except Exception as e:
                    logger.warning(f"  Error en {current_id}: {e}")
                    consecutive_errors += 1
                    current_id += 1
            
            logger.info(f"  {game['name']}: {nuevos} nuevos sorteos guardados")
            await browser.close()
            return {'juego': game['name'], 'nuevos': nuevos}
            
        except Exception as e:
            logger.error(f"Error en {game['name']}: {e}")
            await browser.close()
            return None


def guardar_resultado(game: Dict, sorteo_id: int, data: Dict):
    """Guarda el resultado en el CSV usando los parsers existentes"""
    csv_path = game['csv']
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Usar parser según el juego
    if game['name'] == "LOTO 3" and PARSERS_OK:
        row = parse_loto3(data)
    elif game['name'] == "LOTO 4" and PARSERS_OK:
        row = parse_loto4(data)
    elif game['name'] == "RACHA" and PARSERS_OK:
        row = parse_racha(data)
    elif game['name'] == "LOTO" and PARSERS_OK:
        row = parse_loto_rich(data)
    else:
        # Fallback: guardar solo números básicos
        results = data.get('results', [])
        sorted_results = sorted(results, key=lambda x: x.get('order', 999)) if results else []
        ts = data.get('drawDate')
        fecha = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S') if ts else ''
        
        if game['name'] == "LOTO 3":
            row = {
                'sorteo': data.get('drawNumber'),
                'fecha': fecha,
                'n1': sorted_results[0].get('number', 0) if len(sorted_results) > 0 else 0,
                'n2': sorted_results[1].get('number', 0) if len(sorted_results) > 1 else 0,
                'n3': sorted_results[2].get('number', 0) if len(sorted_results) > 2 else 0,
            }
        elif game['name'] == "LOTO 4":
            row = {
                'sorteo': data.get('drawNumber'),
                'fecha': fecha,
                'n1': sorted_results[0].get('number', 0) if len(sorted_results) > 0 else 0,
                'n2': sorted_results[1].get('number', 0) if len(sorted_results) > 1 else 0,
                'n3': sorted_results[2].get('number', 0) if len(sorted_results) > 2 else 0,
                'n4': sorted_results[3].get('number', 0) if len(sorted_results) > 3 else 0,
            }
        elif game['name'] == "LOTO":
            row = {
                'sorteo': data.get('drawNumber'),
                'fecha': fecha,
                'LOTO_n1': sorted_results[0].get('number', 0) if len(sorted_results) > 0 else 0,
                'LOTO_n2': sorted_results[1].get('number', 0) if len(sorted_results) > 1 else 0,
                'LOTO_n3': sorted_results[2].get('number', 0) if len(sorted_results) > 2 else 0,
                'LOTO_n4': sorted_results[3].get('number', 0) if len(sorted_results) > 3 else 0,
                'LOTO_n5': sorted_results[4].get('number', 0) if len(sorted_results) > 4 else 0,
                'LOTO_n6': sorted_results[5].get('number', 0) if len(sorted_results) > 5 else 0,
            }
        elif game['name'] == "RACHA":
            row = {
                'sorteo': data.get('drawNumber'),
                'fecha': fecha,
                **{f'n{i+1}': sorted_results[i].get('number', 0) for i in range(min(10, len(sorted_results)))}
            }
        else:
            return
    
    # Guardar en CSV
    existe = os.path.exists(csv_path)
    
    # Usar headers del archivo existente si existe, para mantener orden
    if existe:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
    else:
        headers = list(row.keys())
    
    logger.info(f"Row sample: n1={row.get('n1')}, n2={row.get('n2')}, n3={row.get('n3')}")
    
    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        if not existe:
            writer.writeheader()
        writer.writerow(row)


async def scrape_todos_los_juegos() -> List[Dict]:
    """Scrapea todos los juegos"""
    resultados = []
    
    for game in GAME_CONFIG:
        resultado = await scrape_juego(game)
        if resultado:
            resultados.append(resultado)
    
    return resultados


async def scrape_un_juego(nombre_juego: str) -> Optional[Dict]:
    """Scrapea un juego específico"""
    game = next((g for g in GAME_CONFIG if g['name'].lower() == nombre_juego.lower()), None)
    
    if not game:
        logger.error(f"Juego no encontrado: {nombre_juego}")
        return None
    
    return await scrape_juego(game)


# =============================================================================
# EVALUACIÓN POST-SCRAPING
# =============================================================================

def evaluar_predicciones_del_juego(juego: str, numeros_reales: List[int], numero_sorteo: int = None) -> bool:
    """
    Evalúa las predicciones pendientes con el resultado real.
    """
    try:
        # Importar evaluador
        sys.path.insert(0, CURRENT_DIR)
        from loto_orquestador import evaluar_predicciones
        from telegram_notifier import TelegramNotifier
        
        notifier = TelegramNotifier()
        
        resultado = {
            'juego': juego,
            'numeros': numeros_reales,
            'sorteo': numero_sorteo
        }
        
        return evaluar_predicciones(resultado, notifier)
        
    except Exception as e:
        logger.warning(f"Error en evaluación: {e}")
        return False


def obtener_ultimo_resultado(csv_path: str) -> Optional[Dict]:
    """Obtiene el último resultado guardado en el CSV"""
    if not os.path.exists(csv_path):
        return None
    
    try:
        df = pd.read_csv(csv_path)
        if len(df) == 0:
            return None
        
        ultimo = df.iloc[-1]
        
        # Detectar juego por columnas
        if 'LOTO_n1' in df.columns:
            juego = "LOTO"
            numeros = [ultimo.get(f'LOTO_n{i}', 0) for i in range(1, 7)]
        elif 'n4' in df.columns:
            juego = "LOTO4"
            numeros = [ultimo.get(f'n{i}', 0) for i in range(1, 5)]
        elif 'n3' in df.columns:
            juego = "LOTO3"
            numeros = [ultimo.get(f'n{i}', 0) for i in range(1, 4)]
        elif 'n10' in df.columns:
            juego = "RACHA"
            numeros = [ultimo.get(f'n{i}', 0) for i in range(1, 11)]
        else:
            return None
        
        return {
            'juego': juego,
            'sorteo': ultimo.get('sorteo'),
            'numeros': numeros,
            'fecha': ultimo.get('fecha')
        }
        
    except Exception as e:
        logger.warning(f"Error leyendo último resultado: {e}")
        return None


def procesar_y_evaluar(game_name: str, csv_path: str) -> bool:
    """
    Procesa el último resultado y evalúa predicciones.
    """
    resultado = obtener_ultimo_resultado(csv_path)
    
    if resultado:
        logger.info(f"🎯 Evaluando predicciones para {game_name}...")
        return evaluar_predicciones_del_juego(
            resultado['juego'], 
            resultado['numeros'],
            resultado.get('sorteo')
        )
    
    return False


# Main
if __name__ == "__main__":
    import sys
    
    # Flags
    evaluar = '--eval' in sys.argv or '-e' in sys.argv
    
    if len(sys.argv) > 1 and '--eval' not in sys.argv and '-e' not in sys.argv:
        # Modo: scrape un juego específico
        nombre = sys.argv[1]
        asyncio.run(scrape_un_juego(nombre))
        
        if evaluar:
            # Encontrar el juego y evaluar
            game = next((g for g in GAME_CONFIG if g['name'].lower() == nombre.lower()), None)
            if game:
                procesar_y_evaluar(game['name'], game['csv'])
    else:
        # Modo: scrape todos los juegos
        resultados = asyncio.run(scrape_todos_los_juegos())
        print(f"[OK] {len(resultados)} juegos procesados")
        
        if evaluar:
            # Evaluar cada juego
            for game in GAME_CONFIG:
                procesar_y_evaluar(game['name'], game['csv'])
