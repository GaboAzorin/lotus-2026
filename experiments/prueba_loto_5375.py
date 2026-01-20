import os
import requests
import urllib.parse
import re
import json
import uuid

# --- CONFIGURACIÓN ---
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID = "5271" 
DRAW_ID = "5375"

# Obtener Token Scrape.do
SCRAPEDO_TOKEN_RAW = os.environ.get("SCRAPEDO_TOKEN")
if not SCRAPEDO_TOKEN_RAW:
    print("❌ Error: No se encontró la variable SCRAPEDO_TOKEN.")
    exit(1)
SCRAPEDO_TOKEN = SCRAPEDO_TOKEN_RAW.split(",")[0].strip()
print(f"🔑 Usando API Key Scrape.do: {SCRAPEDO_TOKEN[:4]}...{SCRAPEDO_TOKEN[-4:]}")

# Generar un SESSION_ID único para mantener la IP en Scrape.do
SESSION_ID = str(uuid.uuid4())[:8]
print(f"🔗 Session ID generado: {SESSION_ID}")

# Variable global para guardar cookies de la primera petición
COOKIES_RAW = ""

# User-Agent Fijo para mantener consistencia
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_csrf_token():
    global COOKIES_RAW
    print(f"🌍 Paso 1: Visitando Polla.cl para obtener CSRF Token...")
    encoded_url = urllib.parse.quote(BASE_URL)
    
    # Añadimos session_id para mantener la IP
    # IMPORTANTE: Quitamos render=true para recibir los headers raw (cookies)
    target = f"http://api.scrape.do?token={SCRAPEDO_TOKEN}&url={encoded_url}&super=true&geoCode=cl&session={SESSION_ID}"
    
    headers_step1 = {
        "User-Agent": USER_AGENT
    }

    try:
        # Enviamos User-Agent custom también en el paso 1
        resp = requests.get(target, headers=headers_step1, timeout=90)
        
        print("🔍 DEPURACIÓN DE HEADERS (Paso 1):")
        for k, v in resp.headers.items():
            # Filtramos headers irrelevantes de Scrape.do/Cloudflare para no ensuciar el log
            if k.lower() not in ['date', 'content-length', 'connection', 'cf-ray', 'server']:
                print(f"   🔹 {k}: {v}")

        # Extracción manual de cookies desde headers
        cookie_parts = []
        if 'Set-Cookie' in resp.headers:
            raw_cookies = resp.headers['Set-Cookie']
            print(f"🍪 Header Set-Cookie detectado: {raw_cookies[:50]}...")
            COOKIES_RAW = raw_cookies
        
        # Fallback: intentar sacar del CookieJar
        if not COOKIES_RAW and resp.cookies:
            c_list = []
            for c in resp.cookies:
                c_list.append(f"{c.name}={c.value}")
            COOKIES_RAW = "; ".join(c_list)
            print(f"🍪 Cookies extraídas del Jar: {COOKIES_RAW}")

        if not COOKIES_RAW:
            print("⚠️ No se detectaron cookies en la respuesta (ni headers ni jar).")

        if resp.status_code != 200:
            print(f"❌ Error HTTP {resp.status_code} al visitar página base.")
            raise Exception(f"Status {resp.status_code}")
        
        content = resp.text
        token = None
        
        m_json = re.search(r'"csrfToken"\s*:\s*"([a-zA-Z0-9]+)"', content)
        if m_json: 
            token = m_json.group(1)
            print("✅ Token encontrado en JSON script.")
        
        if not token:
            m_input = re.search(r'name="csrfToken"\s+value="([^"]+)"', content)
            if m_input: 
                token = m_input.group(1)
                print("✅ Token encontrado en HTML input.")
            
        if not token:
            raise Exception("No se pudo extraer el token CSRF del HTML.")
            
        return token
    except Exception as e:
        print(f"❌ Fallo al obtener token: {e}")
        raise

def get_specific_draw(csrf_token):
    print(f"🔍 Paso 2: Consultando datos del Sorteo #{DRAW_ID} (Juego {GAME_ID})...")
    encoded_api = urllib.parse.quote(API_URL)
    
    # Usamos el mismo session_id para reutilizar el proxy IP
    target = f"http://api.scrape.do?token={SCRAPEDO_TOKEN}&url={encoded_api}&geoCode=cl&super=true&session={SESSION_ID}"
    
    payload = {
        "gameId": GAME_ID,
        "drawId": DRAW_ID,
        "csrfToken": csrf_token
    }
    
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": USER_AGENT
    }
    
    # Inyectar cookies manualmente en el header
    if COOKIES_RAW:
        # Limpieza básica: si es un string directo de Set-Cookie, a veces funciona reenviarlo,
        # pero lo ideal es enviar solo key=value.
        # Intentaremos enviarlo en el header 'Cookie'.
        headers["Cookie"] = COOKIES_RAW
        print(f"🍪 Inyectando Cookie header: {COOKIES_RAW[:50]}...")
    
    print("📤 Headers enviados en paso 2:")
    for k, v in headers.items():
        print(f"   🔹 {k}: {v}")

    try:
        # Pasamos las cookies capturadas en el paso 1
        resp = requests.post(target, data=payload, headers=headers, timeout=60)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print("✅ ¡Datos recibidos exitosamente!")
                return data
            except json.JSONDecodeError:
                print("❌ La respuesta no es un JSON válido.")
                print(f"Contenido recibido (primeros 2000 chars): {resp.text[:2000]}")
                return None
        else:
            print(f"❌ Error API: Status {resp.status_code}")
            print(f"Respuesta: {resp.text[:2000]}")
            return None
            
    except Exception as e:
        print(f"❌ Error en la petición POST: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Iniciando Prueba Unitaria: Loto Sorteo #5375 (Modo Persistente)")
    print("------------------------------------------------")
    
    try:
        token = get_csrf_token()
        data = get_specific_draw(token)
        
        if data:
            filename = f"loto_{DRAW_ID}_result.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print("------------------------------------------------")
            print(f"💾 Archivo guardado: {filename}")
            if 'drawDate' in data:
                print(f"📅 Fecha del Sorteo: {data['drawDate']}")
                print(f"🔢 Números (raw): {data.get('results')}")
            else:
                print("⚠️ Estructura JSON inesperada.")
            print("🎉 Prueba Finalizada con Éxito")
        else:
            print("💀 La prueba falló.")
            exit(1)
            
    except Exception as e:
        print(f"🔥 Error Fatal: {e}")
        exit(1)
