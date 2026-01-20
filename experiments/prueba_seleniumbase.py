from seleniumbase import SB
import sys

TARGET_URL = "https://www.polla.cl/es/view/resultados"

def run_test():
    print(f"\n--- PRUEBA 4: SELENIUMBASE (UC Mode) ---")
    
    # uc=True activa Undetected ChromeDriver
    # headless=True para servidores, aunque a veces detectan headless
    try:
        with SB(uc=True, headless=True, test=True) as sb:
            print(f"Navegando a {TARGET_URL}...")
            sb.open(TARGET_URL)
            sb.sleep(5)
            
            title = sb.get_title()
            print(f"Título: {title}")
            
            if "Access Denied" in title or "Just a moment" in sb.get_page_source():
                print("❌ Bloqueado por WAF.")
            else:
                # Intentar buscar token
                try:
                    token = sb.get_attribute('input[name="csrfToken"]', "value")
                    if token:
                        print(f"✅ ¡ÉXITO! Token encontrado con SeleniumBase: {token[:10]}...")
                    else:
                        print("⚠️ Acceso OK, pero selector de token falló.")
                except Exception:
                    print("⚠️ No pude extraer el token, pero parece que cargó.")
                    
    except Exception as e:
        print(f"❌ Error SeleniumBase: {e}")

if __name__ == "__main__":
    run_test()
