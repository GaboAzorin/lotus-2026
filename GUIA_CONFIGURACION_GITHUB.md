# 🚀 Guía de Configuración para Automatización en GitHub

Esta guía te ayudará a configurar los secretos necesarios para que el bot funcione automáticamente en GitHub Actions, utilizando la nueva estrategia de **"Enjambre de Keys"** para ahorrar costos.

## 1. Obtener API Keys de Scrape.do

Para cubrir el mes completo sin pagar el plan Enterprise, necesitamos usar varias cuentas gratuitas (o un plan básico + cuentas extra).

1.  Ve a [Scrape.do](https://scrape.do) y regístrate.
2.  Copia tu API Token del dashboard.
3.  Repite el proceso con otros correos electrónicos (se recomiendan 4-5 cuentas para tener ~5,000 - 10,000 créditos mensuales en total).

## 2. Configurar el Secreto en GitHub

El bot está programado para leer todas tus keys desde un único secreto, separadas por comas.

1.  Ve a tu repositorio en GitHub.
2.  Haz clic en la pestaña **Settings** (Configuración) en la barra superior.
3.  En el menú lateral izquierdo, busca la sección **Secrets and variables** y haz clic en **Actions**.
4.  Haz clic en el botón verde **New repository secret**.
5.  **Name:** Escribe exactamente: `SCRAPEDO_TOKEN`
6.  **Secret:** Pega tus API Keys separadas por **comas**, sin espacios extra.
    *   *Ejemplo:* `token_cuenta1,token_cuenta2,token_cuenta3,token_cuenta4`
7.  Haz clic en **Add secret**.

## 3. ¿Cómo funciona la Magia? 🧙‍♂️

### Rotación de Keys (Balanceo de Carga)
Cada vez que el bot se despierta, elige una de las keys al azar.
*   Si tienes 5 keys, el consumo se reparte entre las 5 cuentas.
*   Esto evita que se agoten los créditos de una sola cuenta a mitad de mes.

### Horario Inteligente (Smart Schedule)
El bot se despierta **cada hora** (al minuto 5), pero es muy astuto:
1.  Revisa la hora actual de Chile.
2.  Si es hora de un sorteo (ej: 22:00 para Loto, o 14:00 para Loto 3), ejecuta el scraping.
3.  Si NO es hora de sorteo, **se vuelve a dormir inmediatamente**.
    *   Gasto de Scrape.do: **0 créditos**.
    *   Gasto de GitHub: Segundos.

### Red de Seguridad
A las **23:00 hrs**, el bot hace un "barrido final" de todos los juegos para asegurar que no se perdió nada durante el día.

---
**¡Listo! Con esto tu bot operará de forma autónoma y económica.** 🤖
