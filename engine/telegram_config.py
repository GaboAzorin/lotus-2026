"""
Configuración de Telegram para el bot de LOTO
"""
import os

# Token del bot
TELEGRAM_BOT_TOKEN = "8356075160:AAEtFnt7Qfff35ZyrzFMnvFsmvVsQ4anV_I"

# Chat ID del usuario (Gabo)
TELEGRAM_CHAT_ID = "7987361095"

# Configuración de horarios de scraping (Chile)
SCRAPING_SCHEDULE = {
    "LOTO": {
        "dias": [1, 3, 6],  # martes, jueves, domingo
        "horas": [21],
        "check_minutes_after": 50,  # empieza a las 21:50
        "retry_until": 23,  # hasta las 23:00
    },
    "LOTO3": {
        "dias": [0, 1, 2, 3, 4, 5, 6],  # todos los dias
        "horas": [14, 18, 21],
        "check_minutes_after": 3,
        "retry_until": 23,
    },
    "LOTO4": {
        "dias": [0, 1, 2, 3, 4, 5, 6],
        "horas": [14, 21],
        "check_minutes_after": 3,
        "retry_until": 23,
    },
    "RACHA": {
        "dias": [0, 1, 2, 3, 4, 5, 6],
        "horas": [15, 22],
        "check_minutes_after": 3,
        "retry_until": 23,
    },
}

# Horarios de predicción (1 hora antes del sorteo)
PREDICTION_SCHEDULE = {
    "LOTO3": {
        "horas": [13, 17, 20],  # 1 hora antes de 14:00, 18:00, 21:00
    }
}

# Horario de reentrenamiento (00:00)
RETRAIN_HOUR = 0

# Modelo para Cron (más barato: Gemini 2.0 Flash)
CRON_MODEL = "gemini-2.0-flash"
