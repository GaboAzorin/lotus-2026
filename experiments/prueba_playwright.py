import asyncio
from playwright.async_api import async_playwright

TARGET_URL = "https://www.polla.cl/es/view/resultados"

async def run():
    print(f"\n--- PRUEBA 3: PLAYWRIGHT (Modo Stealth Manual) ---")
    async with async_playwright() as p:
        # Argumentos para intentar ocultar que es un bot
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certifcate-errors",
            "--ignore-certifcate-errors-spki-list",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        browser = await p.chromium.launch(headless=True, args=args)
        
        # Crear contexto con viewport real
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-CL",
            timezone_id="America/Santiago"
        )
        
        # Inyectar script para ocultar webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        print(f"Navegando a {TARGET_URL}...")
        try:
            response = await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=40000)
            status = response.status if response else "N/A"
            print(f"Status Code: {status}")
            
            await asyncio.sleep(8) # Espera generosa
            
            # 1. Chequeo de Token
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            
            # 2. Chequeo de Título y Contenido
            title = await page.title()
            print(f"Título: {title}")
            
            if token:
                print(f"✅ ¡ÉXITO TOTAL! Token CSRF obtenido: {token[:10]}...")
            else:
                content = await page.content()
                if "Access Denied" in content or "Just a moment" in content:
                    print("❌ Bloqueado por WAF (Cloudflare/Incapsula).")
                elif status == 403:
                    print("❌ Error 403 Forbidden (IP bloqueada probablemente).")
                else:
                    print("⚠️ Página cargó (Status 200) pero no encontré el token. ¿Estructura cambió?")
                    
        except Exception as e:
            print(f"❌ Error en Playwright: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
