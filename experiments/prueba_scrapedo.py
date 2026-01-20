import requests
import urllib.parse
import re
import sys

# API Key proporcionada por el usuario
# NOTA: En producción, esto debería venir de una variable de entorno (os.environ.get("SCRAPEDO_TOKEN"))
API_TOKEN = "ad46a71c504242c5b2f8b97f761965e74ca7b86c756"
TARGET_URL = "https://www.polla.cl/es/view/resultados"

def test_scrapedo():
    print("\n--- PRUEBA 5: SCRAPE.DO (API Gateway) ---")
    
    # Codificar la URL objetivo para pasarla como parámetro
    encoded_url = urllib.parse.quote(TARGET_URL)
    
    # Construir URL de la API de Scrape.do
    # render=true: Activa un navegador real (headless) en el lado de Scrape.do para ejecutar JS
    # super=true: Usa proxies residenciales de alta calidad
    # geoCode=cl: Fuerza el uso de una IP de Chile (CRUCIAL para polla.cl)
    api_url = f"http://api.scrape.do?token={API_TOKEN}&url={encoded_url}&render=true&super=true&geoCode=cl"
    
    print(f"📡 Conectando a Scrape.do...")
    print(f"   Target: {TARGET_URL}")
    print(f"   Modo: Render JS + Super Proxy + Geo: Chile")
    
    try:
        # Timeout generoso de 60s
        response = requests.get(api_url, timeout=60)
        
        print(f"   Status Code: {response.status_code}")
        
        # Guardar respuesta para debug
        debug_filename = "experiments/scrapedo_response.html"
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        if response.status_code == 200:
            print("   ✅ Conexión exitosa (200 OK)")
            
            # Análisis de contenido
            content = response.text
            
            # 1. Verificar Token CSRF
            # Buscamos patrones comunes de token en el HTML
            token_match = re.search(r'name="csrfToken"\s+value="([^"]+)"', content)
            
            if token_match:
                token = token_match.group(1)
                print(f"   ✅ ¡ÉXITO! Token CSRF encontrado: {token[:15]}...")
            else:
                print("   ⚠️ HTML descargado OK, pero no encontré 'csrfToken' con regex simple.")
                if "Access Denied" in content or "Security Challenge" in content:
                    print("   ❌ Contenido indica bloqueo (WAF/Captcha).")
                else:
                    print(f"   ℹ️ Revisa {debug_filename} para ver qué llegó.")

        elif response.status_code == 403:
            print("   ❌ Error 403: Scrape.do también fue bloqueado o la API Key tiene problemas.")
        elif response.status_code == 401:
            print("   ❌ Error 401: API Key inválida o sin saldo.")
        else:
            print(f"   ❌ Falló la petición. Ver {debug_filename}")
            
    except Exception as e:
        print(f"   ❌ Error de conexión con Scrape.do: {e}")

if __name__ == "__main__":
    test_scrapedo()
