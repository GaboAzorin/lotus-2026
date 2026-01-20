# 🕵️ Informe de Laboratorio: Diagnóstico de Conectividad Polla.cl

## 🚨 Hallazgo Crítico: Bloqueo Imperva (Error 16)
La captura de pantalla (`debug_screenshot.png`) confirma la causa raíz del problema:

*   **Tecnología de Bloqueo:** **Imperva Incapsula**.
*   **Código de Error:** `Error 16` ("This request was blocked by our security service").
*   **Causa:** La IP de origen (`128.24.161.16`) pertenece a **Microsoft Azure** (usada por GitHub Actions). Imperva tiene estas IPs en lista negra por defecto para evitar tráfico automatizado.

## 🧪 Resultados de los Experimentos

| Estrategia | Resultado | Diagnóstico |
| :--- | :--- | :--- |
| **Requests / Curl** | ❌ **403 Forbidden** | Bloqueo inmediato por reputación de IP. |
| **Playwright Stealth** | ❌ **403 Forbidden** | Bloqueo por IP, ni siquiera carga el JS. |
| **SeleniumBase (UC)** | ❌ **Imperva Screen** | Logra cargar el HTML, pero es interceptado por la pantalla de seguridad de Imperva. |

## 💡 Conclusión
**No es posible automatizar el scrapeo desde la nube de GitHub (Ubuntu-latest) sin usar Proxies Residenciales**, ya que Polla.cl bloquea activamente el tráfico proveniente de Datacenters.

## 🚀 Solución Recomendada: GitHub Self-Hosted Runner
Para automatizar el proceso sin costo (sin comprar proxies) y manteniendo la eficacia de tu IP local, la solución profesional es configurar tu PC como un **Runner de GitHub**.

### ¿Cómo funciona?
1.  Tu PC escucha a GitHub.
2.  GitHub Actions le envía la orden "Ejecutar Scraper".
3.  Tu PC ejecuta el script usando **tu internet de casa** (que ya sabemos que funciona).
4.  Al terminar, sube los resultados y apaga el proceso.

Esto combina lo mejor de dos mundos: **Automatización programada** (cron) + **IP Residencial confiable**.

---
*Este reporte se generó automáticamente tras las pruebas de evasión fallidas.*
