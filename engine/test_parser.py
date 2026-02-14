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
        
        # Probar API con LOTO3 - un ID que ya know tiene datos
        response = await page.request.post(
            'https://www.polla.cl/es/get/draw/results',
            data={'gameId': '2181', 'drawId': '24039', 'csrfToken': token},
            headers={'x-requested-with': 'XMLHttpRequest', 'Origin': 'https://www.polla.cl'}
        )
        
        data = await response.json()
        print("=== RAW API Response ===")
        print(json.dumps(data, indent=2)[:2000])
        
        # Test parser
        sys.path.insert(0, 'C:/Users/Gabriel/Documents/Python/lotus-2026/engine/scrapers')
        from loto_parsers_mix import parse_loto3
        parsed = parse_loto3(data)
        print("\n=== Parsed ===")
        print(parsed)
        
        await browser.close()

import sys
asyncio.run(test())
