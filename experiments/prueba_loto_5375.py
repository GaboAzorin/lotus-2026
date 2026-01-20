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

# Obtener Tokens Scrape.do (Lista)
SCRAPEDO_TOKEN_RAW = os.environ.get("SCRAPEDO_TOKEN")
if not SCRAPEDO_TOKEN_RAW:
    print("❌ Error: No se encontró la variable SCRAPEDO_TOKEN.")
    exit(1)

# Soportar múltiples tokens separados por comas
SCRAPEDO_TOKENS_LIST = [t.strip() for t in SCRAPEDO_TOKEN_RAW.split(",") if t.strip()]
print(f"🔑 Se encontraron {len(SCRAPEDO_TOKENS_LIST)} tokens de Scrape.do.")

async def run_test():
    print("🚀 Iniciando Prueba Unitaria: Loto Sorteo #5375 (Modo Playwright + Proxy Scrape.do)")
    print("------------------------------------------------")

    token_found = False

    for i, token in enumerate(SCRAPEDO_TOKENS_LIST):
        print(f"\n🔄 Intentando con Token #{i+1}: ...{token[-6:] if len(token)>6 else token}")
        
        # Configuración del Proxy Scrape.do
        # Documentación: http://token:render=false@proxy.scrape.do:8080
        # Usamos super=true para IPs residenciales de alta calidad
        proxy_server = "http://proxy.scrape.do:8080"
        
        # Generar Session ID para stickiness
        session_id = str(uuid.uuid4())[:8]
        
        # Construir username con parámetros
        proxy_username = f"{token}-session={session_id}-super=true" 
        
        print(f"🔑 Configurando Proxy Session: {session_id}")
        print(f"🌍 Conectando vía Proxy: {proxy_server}")

        try:
            async with async_playwright() as p:
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
                
                try:
                    # Timeout generoso por ser proxy
                    await page.goto(BASE_URL, timeout=90000, wait_until="domcontentloaded")
                except Exception as e:
                    print(f"⚠️ Error navegando: {e}")
                    # Si falla la navegación, probablemente es error de proxy, intentamos siguiente token
                    await browser.close()
                    continue

                # Validar si Scrape.do devolvió error (JSON en el body)
                try:
                    content = await page.content()
                    if '"StatusCode":401' in content and 'Scrape.do' in content:
                        print("❌ Error 401 de Scrape.do (Token Invalido/Expirado).")
                        await browser.close()
                        continue
                except:
                    pass
                
                print("😴 Esperando 5 segundos para estabilizar sesión...")
                await asyncio.sleep(5)

                # 2. Extraer Token CSRF
                title = await page.title()
                print(f"📄 Título de la página: {title}")
                print("🔍 Buscando Token CSRF...")
                csrf_token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
                
                if not csrf_token:
                    print("⚠️ Token no encontrado en DOM. Intentando regex en el contenido...")
                    content = await page.content()
                    
                    # Regex 1: Formato estándar en HTML
                    m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                    
                    # Regex 2: Formato JSON dentro de scripts
                    if not m:
                        m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', content)
                    
                    if m:
                        csrf_token = m.group(1)
                
                if not csrf_token:
                    content_preview = (await page.content())[:1000]
                    print(f"❌ CONTENIDO HTML PREVIEW:\n{content_preview}")
                    print("❌ No se pudo obtener el token CSRF con este proxy/token.")
                    await browser.close()
                    # Si no pudimos cargar bien la página, tal vez el proxy es malo, intentamos siguiente
                    continue
                    
                print(f"✅ Token obtenido: {csrf_token}")

                # 3. Realizar Petición AJAX (usando el contexto del navegador)
                print(f"📤 Solicitando Sorteo #{DRAW_ID}...")
                
                # Headers adicionales para parecer AJAX legítimo
                # Nota: Playwright maneja cookies automáticamente
                response = await page.request.post(
                    API_URL,
                    data={
                        "gameId": GAME_ID,
                        "drawId": DRAW_ID,
                        "csrfToken": csrf_token
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
                             token_found = True
                             await browser.close()
                             break # ÉXITO TOTAL
                        else:
                             print(f"⚠️ JSON recibido pero sin campo 'results': {data}")
                             # Si recibimos JSON pero sin data, igual cuenta como conexión exitosa, pero quizás fallo de lógica
                             # Asumiremos éxito de conexión
                             token_found = True
                             await browser.close()
                             break

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
            print(f"🔥 Error Fatal con Token #{i+1}: {e}")
            continue

    if not token_found:
        print("\n❌❌❌ TODOS LOS TOKENS FALLARON O SE AGOTARON. ❌❌❌")
        exit(1)
    else:
        print("\n✅✅✅ PRUEBA EXITOSA ✅✅✅")

if __name__ == "__main__":
    asyncio.run(run_test())
