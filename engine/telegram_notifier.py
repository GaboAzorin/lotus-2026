"""
Notificador de Telegram para LOTO
Envía mensajes y predicciones al usuario
"""
import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional
import json
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Importar config
from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    """Envía mensajes al bot de Telegram"""
    
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Envía un mensaje de texto"""
        url = f"{self.api_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Mensaje enviado a {self.chat_id}")
                return True
            else:
                logger.error(f"Error al enviar mensaje: {result}")
                return False
        except Exception as e:
            logger.error(f"Excepción al enviar mensaje: {e}")
            return False
    
    def send_prediction(self, juego: str, fecha: str, predicciones: List[Dict]) -> bool:
        """Envía predicciones formateadas"""
        texto = f"🎯 *Predicciones para {juego} | {fecha}*\n\n"
        
        for pred in predicciones:
            alg_name = pred.get("algoritmo", "Unknown")
            numeros = pred.get("numeros", [])
            confianza = pred.get("confianza", 0)
            
            nums_str = ", ".join(str(n) for n in numeros)
            texto += f"• *{alg_name}*: {nums_str} | {confianza}%\n"
        
        return self.send_message(texto)
    
    def send_evaluation(self, juego: str, fecha: str, resultados: List[Dict]) -> bool:
        """Envía resultado de evaluación de predicciones"""
        texto = f"📊 *Evaluación {juego} | {fecha}*\n\n"
        
        for res in resultados:
            alg_name = res.get("algoritmo", "Unknown")
            acierto = res.get("acierto", False)
            numeros_predichos = res.get("numeros_predichos", [])
            numeros_reales = res.get("numeros_reales", [])
            score = res.get("score", 0)
            
            emoji = "✅" if acierto else "❌"
            nums_pred = ", ".join(str(n) for n in numeros_predichos)
            nums_real = ", ".join(str(n) for n in numeros_reales)
            
            texto += f"{emoji} *{alg_name}*: {nums_pred} vs {nums_real} (score: {score})\n"
        
        return self.send_message(texto)
    
    def send_status(self, mensaje: str) -> bool:
        """Envía un mensaje de status"""
        timestamp = datetime.now().strftime("%H:%M")
        texto = f"📌 *LOTO Bot* [{timestamp}]\n{mensaje}"
        return self.send_message(texto)
    
    def send_error(self, mensaje: str) -> bool:
        """Envía un mensaje de error"""
        texto = f"❌ *ERROR*\n{mensaje}"
        return self.send_message(texto)
    
    def send_scraped_result(self, juego: str, numeros: List[int], fecha: str) -> bool:
        """Envía resultado scrapeado"""
        nums_str = ", ".join(str(n) for n in numeros)
        texto = f"🔎 *Resultado {juego}* | {fecha}\n\nNúmeros: *{nums_str}*"
        return self.send_message(texto)


# Instancia global
notifier = TelegramNotifier()


def test_connection() -> bool:
    """Prueba la conexión con el bot"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            bot_info = result.get("result", {})
            logger.info(f"Bot conectado: @{bot_info.get('username')}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error probando bot: {e}")
        return False


if __name__ == "__main__":
    # Test
    test_connection()
    notifier.send_status("🧪 Bot de LOTO iniciado correctamente!")
