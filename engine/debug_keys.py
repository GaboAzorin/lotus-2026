import sys
sys.path.insert(0, 'C:/Users/Gabriel/Documents/Python/lotus-2026/engine/scrapers')
from loto_parsers_mix import parse_loto3
import json
import asyncio
from playwright.async_api import async_playwright
import re
import pandas as pd

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.polla.cl/es/view/resultados', wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        content = await page.content()
        m = re.search(r'"csrfToken":"([a-zA-Z0-9]+)"', content)
        token = m.group(1)
        
        response = await page.request.post(
            'https://www.polla.cl/es/get/draw/results',
            data={'gameId': '2181', 'drawId': '24039', 'csrfToken': token},
            headers={'x-requested-with': 'XMLHttpRequest', 'Origin': 'https://www.polla.cl'}
        )
        
        data = await response.json()
        parsed = parse_loto3(data)
        
        print('=== Keys del parser ===')
        print(list(parsed.keys()))
        print()
        
        # Get CSV headers
        df = pd.read_csv('C:/Users/Gabriel/Documents/Python/lotus-2026/data/LOTO3_MAESTRO.csv')
        print('=== Keys del CSV (original) ===')
        print(list(df.columns))
        
        await browser.close()

asyncio.run(test())
