import os
import asyncio
import json
import uuid
import re
import urllib.parse
from playwright.async_api import async_playwright

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

async def run_test():
    print("🚀 Iniciando Prueba Unitaria: Loto Sorteo #5375 (Modo Playwright + Proxy Scrape.do)")
    print("------------------------------------------------")

    # Configuración del Proxy Scrape.do
    # Documentación: http://token:render=false@proxy.scrape.do:8080
    # Usamos super=true para IPs residenciales de alta calidad
    proxy_server = "http://proxy.scrape.do:8080"
    
    # Generar Session ID para stickiness
    session_id = str(uuid.uuid4())[:8]
    
    # Construir username con parámetros
    proxy_username = f"{SCRAPEDO_TOKEN}-session={session_id}-super=true" 
    
    print(f"🔑 Configurando Proxy Session: {session_id}")
    
    print(f"🌍 Conectando vía Proxy: {proxy_server}")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                proxy={
                    "server": proxy_server,
                    "username": proxy_username,
                    "password": "" # Password suele ser vacío o ignorado
                }
            )
            
            # Crear contexto con User-Agent consistente
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            
            page = await context.new_page()

            # 1. Navegar a la home para obtener sesión y token
            print("⏳ Navegando a Polla.cl...")
            # Timeout generoso por ser proxy
            await page.goto(BASE_URL, timeout=90000, wait_until="domcontentloaded")
            
            print("😴 Esperando 5 segundos para estabilizar sesión...")
            await asyncio.sleep(5)

            # 2. Extraer Token CSRF
            print(f"📄 Título de la página: {await page.title()}")
            print("🔍 Buscando Token CSRF...")
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            
            if not token:
                print("⚠️ Token no encontrado en DOM. Intentando regex en el contenido...")
                content = await page.content()
                
                # Regex 1: Formato estándar en HTML
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                
                # Regex 2: Formato JSON dentro de scripts
                if not m:
                    m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', content)
                
                if m:
                    token = m.group(1)
            
            if not token:
                content_preview = (await page.content())[:1000]
                print(f"❌ CONTENIDO HTML PREVIEW:\n{content_preview}")
                raise Exception("No se pudo obtener el token CSRF.")
                
            print(f"✅ Token obtenido: {token}")

            # 3. Realizar Petición AJAX (usando el contexto del navegador)
            print(f"📤 Solicitando Sorteo #{DRAW_ID}...")
            
            # Headers adicionales para parecer AJAX legítimo
            # Nota: Playwright maneja cookies automáticamente
            response = await page.request.post(
                API_URL,
                data={
                    "gameId": GAME_ID,
                    "drawId": DRAW_ID,
                    "csrfToken": token
                },
                headers={
                    "x-requested-with": "XMLHttpRequest",
                    "Origin": "https://www.polla.cl",
                    "Referer": BASE_URL
                }
            )

            print(f"📥 Status Respuesta: {response.status}")
            
            if response.status == 200:
                try:
                    data = await response.json()
                    print("✅ ¡JSON Recibido!")
                    
                    filename = f"loto_{DRAW_ID}_result_playwright.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    print(f"💾 Guardado en: {filename}")
                    
                    if 'results' in data:
                         print(f"🔢 Resultados: {data['results']}")
                    else:
                         print(f"⚠️ JSON recibido pero sin campo 'results': {data}")

                except Exception as e:
                    text = await response.text()
                    print(f"❌ Error decodificando JSON: {e}")
                    print(f"📄 Contenido raw: {text[:500]}...")
            else:
                print(f"❌ Error HTTP: {response.status}")
                text = await response.text()
                print(f"📄 Respuesta: {text[:500]}...")

            await browser.close()

        except Exception as e:
            print(f"🔥 Error Fatal en Playwright: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
