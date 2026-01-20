import requests
import sys

TARGET_URL = "https://www.polla.cl/es/view/resultados"

def test_requests():
    print("\n--- PRUEBA 1: REQUESTS ESTÁNDAR ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Conexión exitosa con requests.")
            if "csrfToken" in response.text:
                print("   🔑 Token CSRF detectado en el HTML.")
            else:
                print("   ⚠️ HTML descargado pero no veo el token.")
        else:
            print(f"❌ Bloqueado o error. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

def test_curl_cffi():
    print("\n--- PRUEBA 2: CURL_CFFI (Impersonate Browser) ---")
    try:
        from curl_cffi import requests as crequests
        # Impersonate Chrome 120
        response = crequests.get(TARGET_URL, impersonate="chrome120", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Conexión exitosa con curl_cffi.")
            if "csrfToken" in response.text:
                print("   🔑 Token CSRF detectado en el HTML.")
            else:
                print("   ⚠️ HTML descargado pero no veo el token.")
        else:
            print(f"❌ Bloqueado o error. Status: {response.status_code}")
    except ImportError:
        print("⚠️ curl_cffi no está instalado. Saltando prueba.")
    except Exception as e:
        print(f"❌ Error con curl_cffi: {e}")

if __name__ == "__main__":
    print(f"Target: {TARGET_URL}")
    test_requests()
    test_curl_cffi()
