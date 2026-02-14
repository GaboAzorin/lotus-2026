import asyncio
from playwright.async_api import async_playwright
import re
import json

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.polla.cl/es/view/resultados', wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        # Obtener token
        content = await page.content()
        m = re.search(r'"csrfToken":"([a-zA-Z0-9]+)"', content)
        token = m.group(1) if m else None
        print(f"Token: {token[:20]}...")
        
        # Probar API con LOTO3 - buscar sorteos con resultados
        found = False
        for test_id in range(24038, 23500, -1):
            if found:
                break
            response = await page.request.post(
                'https://www.polla.cl/es/get/draw/results',
                data={'gameId': '2181', 'drawId': str(test_id), 'csrfToken': token},
                headers={'x-requested-with': 'XMLHttpRequest', 'Origin': 'https://www.polla.cl'}
            )
            
            data = await response.json()
            success = data.get('success')
            has_data = 'data' in data or 'results' in data
            print(f"ID {test_id}: success={success}, has_data={has_data}")
            
            status = data.get('status')
            print(f"ID {test_id}: status={status}")
            
            # Status 3 o 4 significa sorteado con resultados
            if status and status in [3, 4]:
                print(f"  Found SORTEDOR with status {status}!")
                print(f"  Full response: {json.dumps(data, indent=2)[:1500]}")
                found = True
                break
        
        await browser.close()

asyncio.run(test())
