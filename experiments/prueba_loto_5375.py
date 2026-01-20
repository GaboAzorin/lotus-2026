import os
import requests
import urllib.parse
import re
import json

# --- CONFIGURACIÓN ---
# URL base para obtener el token CSRF (simulando visita humana)
BASE_URL = "https://www.polla.cl/es/view/resultados"

# Endpoint AJAX para obtener datos del sorteo
API_URL = "https://www.polla.cl/es/get/draw/results"

# Identificadores específicos para esta prueba
# LOTO Game ID = 5271 (Este ID es constante para Loto Clásico)
GAME_ID = "5271" 
# Sorteo solicitado por el usuario
DRAW_ID = "5375"

# Obtener Token Scrape.do desde variables de entorno
SCRAPEDO_TOKEN_RAW = os.environ.get("SCRAPEDO_TOKEN")

if not SCRAPEDO_TOKEN_RAW:
    print("❌ Error: No se encontró la variable SCRAPEDO_TOKEN.")
    exit(1)

# Tomamos la primera key disponible si hay varias
SCRAPEDO_TOKEN = SCRAPEDO_TOKEN_RAW.split(",")[0].strip()
print(f"🔑 Usando API Key Scrape.do: {SCRAPEDO_TOKEN[:4]}...{SCRAPEDO_TOKEN[-4:]}")

def get_csrf_token():
    """
    Paso 1: Visitar la página de resultados para obtener el token CSRF.
    """
    print(f"🌍 Paso 1: Visitando Polla.cl para obtener CSRF Token...")
    encoded_url = urllib.parse.quote(BASE_URL)
    
    # Parámetros Scrape.do:
    # render=true: Renderiza JS (necesario si el token se genera dinámicamente)
    # super=true: Usa proxies residenciales premium (evita bloqueos 403)
    # geoCode=cl: Geolocalización Chile (vital para Polla.cl)
    target = f"http://api.scrape.do?token={SCRAPEDO_TOKEN}&url={encoded_url}&render=true&super=true&geoCode=cl"
    
    try:
        resp = requests.get(target, timeout=90)
        if resp.status_code != 200:
            print(f"❌ Error HTTP {resp.status_code} al visitar página base.")
            print(f"Respuesta parcial: {resp.text[:200]}")
            raise Exception(f"Status {resp.status_code}")
        
        content = resp.text
        token = None
        
        # Estrategia 1: Buscar en JSON incrustado (patrón más común reciente)
        # "csrfToken": "abc..."
        m_json = re.search(r'"csrfToken"\s*:\s*"([a-zA-Z0-9]+)"', content)
        if m_json: 
            token = m_json.group(1)
            print("✅ Token encontrado en JSON script.")
        
        # Estrategia 2: Buscar en input hidden (patrón clásico HTML)
        # <input name="csrfToken" value="abc...">
        if not token:
            m_input = re.search(r'name="csrfToken"\s+value="([^"]+)"', content)
            if m_input: 
                token = m_input.group(1)
                print("✅ Token encontrado en HTML input.")
            
        if not token:
            # Guardar HTML para debug si falla
            with open("debug_fail_token.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("📸 HTML guardado en 'debug_fail_token.html'")
            raise Exception("No se pudo extraer el token CSRF del HTML.")
            
        return token
    except Exception as e:
        print(f"❌ Fallo al obtener token: {e}")
        raise

def get_specific_draw(csrf_token):
    """
    Paso 2: Consultar la API interna de Polla para el sorteo específico.
    """
    print(f"🔍 Paso 2: Consultando datos del Sorteo #{DRAW_ID} (Juego {GAME_ID})...")
    encoded_api = urllib.parse.quote(API_URL)
    
    # Nota: Para la petición POST a la API, Scrape.do recomienda pasar los parámetros
    # en la URL del proxy y el payload en el body.
    target = f"http://api.scrape.do?token={SCRAPEDO_TOKEN}&url={encoded_api}&geoCode=cl&super=true"
    
    payload = {
        "gameId": GAME_ID,
        "drawId": DRAW_ID,
        "csrfToken": csrf_token
    }
    
    # Headers simulando una petición AJAX legítima
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.post(target, data=payload, headers=headers, timeout=60)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print("✅ ¡Datos recibidos exitosamente!")
                return data
            except json.JSONDecodeError:
                print("❌ La respuesta no es un JSON válido.")
                print(f"Contenido recibido: {resp.text[:500]}")
                return None
        else:
            print(f"❌ Error API: Status {resp.status_code}")
            print(f"Respuesta: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Error en la petición POST: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Iniciando Prueba Unitaria: Loto Sorteo #5375")
    print("------------------------------------------------")
    
    try:
        # 1. Obtener Token
        token = get_csrf_token()
        
        # 2. Obtener Datos
        data = get_specific_draw(token)
        
        if data:
            # 3. Guardar Resultado
            filename = f"loto_{DRAW_ID}_result.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print("------------------------------------------------")
            print(f"💾 Archivo guardado: {filename}")
            
            # 4. Mostrar resumen en consola
            if 'drawDate' in data:
                print(f"📅 Fecha del Sorteo: {data['drawDate']}")
                print(f"🔢 Números (raw): {data.get('results')}")
                if 'totalWinners' in data:
                    print(f"🏆 Ganadores Totales: {data['totalWinners']}")
            else:
                print("⚠️ El JSON no tiene la estructura esperada (campo 'drawDate' faltante).")
                
            print("🎉 Prueba Finalizada con Éxito")
        else:
            print("💀 La prueba falló en la etapa de obtención de datos.")
            exit(1)
            
    except Exception as e:
        print(f"🔥 Error Fatal: {e}")
        exit(1)
