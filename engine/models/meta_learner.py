import pandas as pd
import numpy as np
import joblib
import os
import json
import math
from sklearn.ensemble import RandomForestRegressor

# Configuración
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
MODEL_FILE = os.path.join(DATA_DIR, 'meta_learner_model.pkl')
MAPS_FILE = os.path.join(DATA_DIR, 'meta_learner_maps.json') # NUEVO: Para persistir IDs
SIMULACIONES_FILE = os.path.join(DATA_DIR, 'LOTO_SIMULACIONES.csv')

class MetaLearner:
    def __init__(self):
        self.model = self.cargar_modelo()
        self.maps = self.cargar_mapas()

    def cargar_modelo(self):
        if os.path.exists(MODEL_FILE):
            return joblib.load(MODEL_FILE)
        return None

    def cargar_mapas(self):
        if os.path.exists(MAPS_FILE):
            with open(MAPS_FILE, 'r') as f: return json.load(f)
        return {"algos": {}, "juegos": {}}

    def entrenar(self):
        if not os.path.exists(SIMULACIONES_FILE): return
        
        df = pd.read_csv(SIMULACIONES_FILE)
        df_audit = df[df['estado'] == 'AUDITADO'].copy()
        if len(df_audit) < 300: return 

        # 1. Ingeniería de Características Pro
        # Creamos mapeos reales y los persistimos
        df_audit['alg_id'], alg_map = pd.factorize(df_audit['algoritmo'])
        df_audit['juego_id'], juego_map = pd.factorize(df_audit['juego'])
        
        self.maps['algos'] = {name: i for i, name in enumerate(alg_map)}
        self.maps['juegos'] = {name: i for i, name in enumerate(juego_map)}
        
        # Guardamos los mapas para que la predicción use las mismas IDs
        with open(MAPS_FILE, 'w') as f: json.dump(self.maps, f)

        # X = [ID Juego, ID Algo, Hora, Score ADN]
        X = df_audit[['juego_id', 'alg_id', 'hora_dia', 'score_afinidad']]
        y = df_audit['aciertos'] 

        # 2. Entrenamiento con regularización (para no sobreajustar al azar)
        model = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
        model.fit(X, y)
        
        joblib.dump(model, MODEL_FILE)
        self.model = model
        print(f"🧠 META-LEARNER: Cerebro de nivel 2 actualizado con {len(df_audit)} experiencias.")

    def predecir_confianza_real(self, juego, algoritmo, hora, score_adn):
        """
        Devuelve el multiplicador de peso basado en la probabilidad de éxito real.
        Usa escalado SIGMOIDE para evitar divergencia a infinito.
        Rango de salida: [0.5, 3.0] - nunca diverge.
        """
        if not self.model or not self.maps['algos']: return 1.0

        # Máximo de aciertos por juego para normalizar
        MAX_ACIERTOS = {'LOTO': 6, 'LOTO3': 3, 'LOTO4': 4, 'RACHA': 10}

        try:
            j_id = self.maps['juegos'].get(juego, -1)
            a_id = self.maps['algos'].get(algoritmo, -1)

            if j_id == -1 or a_id == -1: return 1.0

            input_data = np.array([[j_id, a_id, hora, score_adn]])
            esperanza_aciertos = self.model.predict(input_data)[0]

            # Normalizar por el máximo del juego
            max_juego = MAX_ACIERTOS.get(juego, 6)
            esperanza_normalizada = esperanza_aciertos / max_juego

            # ESCALADO SIGMOIDE: evita divergencia, siempre entre 0.5 y 3.0
            # sigmoide(x) = 1 / (1 + e^(-k*x)) donde k controla la pendiente
            k = 4.0  # Factor de pendiente (ajustable)
            sigmoide = 1.0 / (1.0 + math.exp(-k * (esperanza_normalizada - 0.3)))

            # Mapear sigmoide [0,1] a multiplicador [0.5, 3.0]
            multiplicador = 0.5 + (sigmoide * 2.5)

            return multiplicador
        except Exception as e:
            return 1.0