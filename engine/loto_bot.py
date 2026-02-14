"""
Bot interactivo de Telegram para LOTO
Maneja comandos del usuario: /start, /predicciones, /status, /resultados, /ayuda
"""
import os
import sys
import json
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Configurar paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importar config y notificador
from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from telegram_notifier import TelegramNotifier
from loto_orquestador import generar_predicciones_loto3, evaluar_predicciones

# Paths
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
CSV_SIMULACIONES = os.path.join(DATA_DIR, 'LOTO_SIMULACIONES.csv')
CSV_LOTO3 = os.path.join(DATA_DIR, 'LOTO3_MAESTRO.csv')


# =============================================================================
# MANEJO DE COMANDOS
# =============================================================================

class LOTOBot:
    """Maneja los comandos del bot de Telegram"""
    
    def __init__(self):
        self.notifier = TelegramNotifier()
    
    def handle_command(self, comando: str, args: List[str] = None) -> str:
        """Procesa un comando y retorna la respuesta"""
        comando = comando.lower().strip()
        
        if comando in ['/start', '/ayuda', '/help']:
            return self.cmd_ayuda()
        
        elif comando == '/predicciones':
            return self.cmd_predicciones()
        
        elif comando == '/status':
            return self.cmd_status()
        
        elif comando == '/resultados':
            return self.cmd_resultados(args)
        
        elif comando == '/historial':
            return self.cmd_historial(args)
        
        elif comando == '/eval':
            return self.cmd_eval(args)
        
        elif comando == '/probar':
            return self.cmd_probar()
        
        else:
            return f"❓ Comando no reconocido: {comando}\nUsa /ayuda para ver los comandos disponibles."
    
    def cmd_ayuda(self) -> str:
        """Muestra la ayuda"""
        return """🎰 *LOTO Bot - Comandos disponibles*

• /start - Muestra este mensaje
• /predicciones - Genera nuevas predicciones
• /status - Muestra el estado del sistema
• /resultados [juego] - Últimos resultados (LOTO3, LOTO4, RACHA)
• /historial [juego] - Ver predicciones anteriores
• /eval [juego] [numeros] - Evaluar una predicción
• /probar - Prueba de conexión

*Ejemplos:*
/resultados LOTO3
/historial LOTO3
/eval LOTO3 5 7 2"""
    
    def cmd_predicciones(self) -> str:
        """Genera nuevas predicciones"""
        logger.info("Generando predicciones por comando...")
        
        try:
            # Generar predicciones
            generar_predicciones_loto3(self.notifier)
            
            return "✅ *Predicciones generadas*\n\nLas predicciones se han enviado y guardado."
            
        except Exception as e:
            logger.error(f"Error generando predicciones: {e}")
            return f"❌ Error: {e}"
    
    def cmd_status(self) -> str:
        """Muestra el estado del sistema"""
        try:
            import pandas as pd
            
            # Contar predicciones
            if os.path.exists(CSV_SIMULACIONES):
                df = pd.read_csv(CSV_SIMULACIONES)
                total = len(df)
                pendientes = len(df[df['estado'] == 'PENDIENTE'])
                auditadas = len(df[df['estado'] == 'AUDITADO'])
                
                # Último resultado
                ultimo = df[df['estado'] == 'AUDITADO'].tail(1)
                if len(ultimo) > 0:
                    ultimo_msg = f"Última evaluación: {ultimo.iloc[0]['juego']} - {ultimo.iloc[0]['aciertos']} aciertos"
                else:
                    ultimo_msg = "Sin evaluaciones aún"
            else:
                total = pendientes = auditadas = 0
                ultimo_msg = "Sin datos"
            
            # Próximos sorteos
            ahora = datetime.now()
            sorteos = []
            for h in [14, 18, 21]:
                if ahora.hour < h:
                    sorteos.append(f"{h}:00")
            if not sorteos:
                sorteos = ["14:00 (mañana)"]
            
            return f"""📊 *Estado del Sistema*

• Total predicciones: {total}
• Pendientes: {pendientes}
• Auditadas: {auditadas}

🕐 *Próximos sorteos LOTO3:*
{', '.join(sorteos)}

{ultimo_msg}"""
            
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_resultados(self, args: List[str]) -> str:
        """Muestra los últimos resultados"""
        try:
            import pandas as pd
            
            juego = args[0].upper() if args else 'LOTO3'
            
            # Mapping de juegos a CSVs
            csv_map = {
                'LOTO3': CSV_LOTO3,
                'LOTO4': os.path.join(DATA_DIR, 'LOTO4_MAESTRO.csv'),
                'RACHA': os.path.join(DATA_DIR, 'RACHA_MAESTRO.csv'),
                'LOTO': os.path.join(DATA_DIR, 'LOTO_HISTORIAL_MAESTRO.csv'),
            }
            
            csv_path = csv_map.get(juego)
            if not csv_path or not os.path.exists(csv_path):
                return f"❌ Juego no válido: {juego}\nUsos: LOTO3, LOTO4, RACHA, LOTO"
            
            df = pd.read_csv(csv_path)
            ultimos = df.tail(5)
            
            mensaje = f"📋 *Últimos resultados {juego}*\n\n"
            
            for idx, row in ultimos.iterrows():
                fecha = row.get('fecha', '')[:10]
                if juego == 'LOTO3':
                    n1 = row.get('n1', '')
                    n2 = row.get('n2', '')
                    n3 = row.get('n3', '')
                    nums = f"{n1} - {n2} - {n3}"
                elif juego == 'LOTO4':
                    nums = " - ".join(str(row.get(f'n{i}', '')) for i in range(1, 5))
                elif juego == 'RACHA':
                    nums = " - ".join(str(row.get(f'n{i}', '')) for i in range(1, 11))
                else:  # LOTO
                    nums = " - ".join(str(row.get(f'LOTO_n{i}', '')) for i in range(1, 7))
                
                mensaje += f"• *{fecha}*: {nums}\n"
            
            return mensaje
            
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_historial(self, args: List[str]) -> str:
        """Muestra el historial de predicciones"""
        try:
            import pandas as pd
            
            juego = args[0].upper() if args else 'LOTO3'
            
            if not os.path.exists(CSV_SIMULACIONES):
                return "❌ No hay predicciones guardadas"
            
            df = pd.read_csv(CSV_SIMULACIONES)
            df_juego = df[df['juego'] == juego].tail(10)
            
            if len(df_juego) == 0:
                return f"❌ No hay predicciones para {juego}"
            
            mensaje = f"📈 *Historial {juego}*\n\n"
            
            for idx, row in df_juego.iterrows():
                estado = row.get('estado', '')
                algoritmo = row.get('algoritmo', '')
                numeros = row.get('numeros', '')
                aciertos = row.get('aciertos', 0)
                score = row.get('score', 0)
                
                # Limpiar numeros
                try:
                    nums = json.loads(numeros.replace("'", '"'))
                    nums_str = "-".join(str(n) for n in nums)
                except:
                    nums_str = str(numeros)[:20]
                
                emoji = "✅" if estado == "AUDITADO" else "⏳"
                mensaje += f"{emoji} *{algoritmo}* [{nums_str}]: {aciertos} aciertos (score: {score})\n"
            
            return mensaje
            
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_eval(self, args: List[str]) -> str:
        """Evalúa una predicción manualmente"""
        try:
            if not args or len(args) < 4:
                return "❌ Uso: /eval LOTO3 5 7 2\nO: /eval 5 7 2 (usa LOTO3 por defecto)"
            
            # Parsear argumentos
            if args[0].upper() in ['LOTO3', 'LOTO4', 'RACHA', 'LOTO']:
                juego = args[0].upper()
                numeros = [int(args[1]), int(args[2]), int(args[3])]
            else:
                juego = 'LOTO3'
                numeros = [int(args[0]), int(args[1]), int(args[2])]
            
            resultado = {
                'juego': juego,
                'numeros': numeros
            }
            
            evaluar_predicciones(resultado, self.notifier)
            
            nums_str = "-".join(str(n) for n in numeros)
            return f"✅ Evaluación enviada para {juego}: {nums_str}"
            
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_probar(self) -> str:
        """Prueba de conexión"""
        if self.notifier.send_status("🧪 Prueba de conexión"):
            return "✅ Conexión exitosa! Mensaje enviado."
        else:
            return "❌ Error de conexión"


# =============================================================================
# MAIN - Handler para Webhook o Polling
# =============================================================================

def handle_update(update: Dict) -> Optional[str]:
    """
    Procesa un update de Telegram (webhook o polling).
    Retorna la respuesta o None.
    """
    try:
        # Extraer mensaje
        if 'message' in update:
            message = update['message']
            chat_id = str(message['chat']['id'])
            text = message.get('text', '')
            
            # Solo responder al usuario configurado
            if chat_id != TELEGRAM_CHAT_ID:
                logger.warning(f"Chat no autorizado: {chat_id}")
                return None
            
            # Parsear comando
            parts = text.split()
            comando = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Ejecutar comando
            bot = LOTOBot()
            return bot.handle_command(comando, args)
        
        elif 'callback_query' in update:
            # Callback de inline buttons
            callback = update['callback_query']
            # Por ahora ignorar
            pass
        
        return None
        
    except Exception as e:
        logger.error(f"Error procesando update: {e}")
        return f"Error: {e}"


# =============================================================================
# POLLING MODE (para testing)
# =============================================================================

def polling_loop():
    """Modo polling para desarrollo/testing"""
    import requests
    import time
    
    offset = 0
    bot = LOTOBot()
    
    logger.info("🔄 Iniciando polling...")
    
    while True:
        try:
            # Obtener updates
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {'timeout': 30, 'offset': offset}
            
            response = requests.get(url, params=params, timeout=35)
            result = response.json()
            
            if result.get('ok'):
                updates = result.get('result', [])
                
                for update in updates:
                    offset = update['update_id'] + 1
                    
                    if 'message' in update:
                        chat_id = str(update['message']['chat']['id'])
                        
                        if chat_id == TELEGRAM_CHAT_ID:
                            text = update['message'].get('text', '')
                            parts = text.split()
                            comando = parts[0]
                            args = parts[1:] if len(parts) > 1 else []
                            
                            respuesta = bot.handle_command(comando, args)
                            
                            if respuesta:
                                # Enviar respuesta
                                send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                                requests.post(send_url, json={
                                    'chat_id': chat_id,
                                    'text': respuesta,
                                    'parse_mode': 'Markdown'
                                })
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en polling: {e}")
            time.sleep(5)


# Test rápido
if __name__ == "__main__":
    # Modo test
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    bot = LOTOBot()
    print(bot.cmd_status())
