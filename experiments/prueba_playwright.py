import asyncio
from playwright.async_api import async_playwright

TARGET_URL = "https://www.polla.cl/es/view/resultados"

async def run():
    print(f"\n--- PRUEBA 3: PLAYWRIGHT HEADLESS ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print(f"Navegando a {TARGET_URL}...")
        try:
            response = await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else "N/A"
            print(f"Status Code: {status}")
            
            await asyncio.sleep(5) # Esperar carga de scripts
            
            # Intentar buscar token
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            if token:
                print(f"✅ ¡ÉXITO! Token CSRF obtenido: {token[:10]}...")
            else:
                content = await page.content()
                if "Access Denied" in content or "Just a moment" in content:
                    print("❌ Detectado bloqueo (Cloudflare/WAF).")
                else:
                    print("⚠️ Página cargó pero no encontré el token por selector estándar.")
                    
            title = await page.title()
            print(f"Título de la página: {title}")
            
        except Exception as e:
            print(f"❌ Error en Playwright: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
