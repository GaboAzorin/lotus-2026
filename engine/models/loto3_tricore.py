import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import json
import os
import logging
import tempfile
import shutil
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ==========================================
# 🧭 NAVEGACIÓN DE RUTAS ABSOLUTA
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

RUTA_DATA = os.path.join(PROJECT_ROOT, "data", "LOTO3_MAESTRO.csv")
RUTA_DASHBOARD = os.path.join(PROJECT_ROOT, "dashboard_data.json")

# ==========================================
# LÓGICA TRI-CORE (CORREGIDA PARA TUS HEADERS)
# ==========================================
class CerebroPosicional:
    """Un mini-modelo dedicado exclusivamente a UNA posición vertical"""
    def __init__(self, posicion_id):
        self.pos_id = posicion_id
        self.model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    
    def preparar_features(self, df):
        # --- CORRECCIÓN CRÍTICA AQUÍ ---
        # Tu CSV tiene columnas 'n1', 'n2', 'n3', NO 'LOTO3_n1'
        col_name = f'n{self.pos_id}'
        
        # Validación de seguridad
        if col_name not in df.columns:
            # Fallback: A veces pandas agrega espacios o cambia mayúsculas
            cols_limpias = [c.strip().lower() for c in df.columns]
            if col_name in cols_limpias:
                col_name = col_name # Está ok pero sucio en el origen
            else:
                raise ValueError(f"Columna '{col_name}' no encontrada. Cabeceras disponibles: {list(df.columns)}")

        df = df.copy()
        
        # 1. Lags (Memoria de corto plazo)
        for i in range(1, 6):
            df[f'lag_{i}'] = df[col_name].shift(i)
        
        # 2. Frecuencia reciente
        df['rolling_mean'] = df[col_name].rolling(window=10).mean()
        
        # 3. Fecha (Ciclos temporales)
        if 'fecha' in df.columns:
            # Manejo robusto de fechas (tu CSV a veces usa formatos distintos)
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce') 
            df['dia_semana'] = df['fecha'].dt.dayofweek
            df['dia_mes'] = df['fecha'].dt.day
        else:
            df['dia_semana'] = df.index % 7
            df['dia_mes'] = df.index % 30
            
        return df.dropna(), col_name

    def entrenar(self, df):
        df_proc, target_col = self.preparar_features(df)
        
        features = [c for c in df_proc.columns if 'lag_' in c or 'dia_' in c or 'rolling' in c]
        
        X = df_proc[features]
        y = df_proc[target_col].astype(int)
        
        self.model.fit(X, y)
        self.last_X = X.iloc[[-1]] 
        return self.model.score(X, y)

    def predecir(self):
        probs = self.model.predict_proba(self.last_X)[0]
        
        # ESTRATEGIA: Selección ponderada de los top 3 para mantener varianza
        top_indices = np.argsort(probs)[-3:] 
        top_probs = probs[top_indices]
        top_probs = top_probs / top_probs.sum()
        
        prediccion = np.random.choice(top_indices, p=top_probs)
        confianza = probs[prediccion]
        
        return int(prediccion), confianza

def ejecutar_sistema_tricore():
    print("🚀 Iniciando Protocolo Tri-Core para LOTO 3...")
    print(f"📂 Raíz del proyecto detectada: {PROJECT_ROOT}")
    
    # 1. Cargar Datos
    if not os.path.exists(RUTA_DATA):
        print(f"❌ Error Crítico: No se encuentra el archivo en {RUTA_DATA}")
        return

    try:
        # Cargamos el CSV. OJO: header=0 asume que la primera fila son los nombres
        df = pd.read_csv(RUTA_DATA)
        print(f"✅ Datos cargados: {len(df)} sorteos históricos.")
        # Debug rápido para ver qué columnas leyó realmente
        print(f"   ℹ️ Columnas detectadas: {list(df.columns[:10])}...") 
    except Exception as e:
        print(f"❌ Error cargando CSV: {e}")
        return

    prediccion_final = []
    confianza_total = 0
    
    # 2. Bucle de Entrenamiento
    for i in range(1, 4):
        print(f"  ⚙️ Entrenando Núcleo Posicional #{i}...")
        try:
            cerebro = CerebroPosicional(i)
            acc = cerebro.entrenar(df)
            num, conf = cerebro.predecir()
            prediccion_final.append(num)
            confianza_total += conf
            print(f"     ✅ Núcleo {i} predice: {num} (Confianza: {conf:.2f})")
        except Exception as e:
            print(f"     ❌ Fallo en Núcleo {i}: {e}")
            prediccion_final.append(0) # Fallback

    # 3. Consolidar Resultado
    score_final = int((confianza_total / 3) * 100)
    
    # Calcular sorteo objetivo
    ultimo_sorteo = 0
    if 'sorteo' in df.columns:
        ultimo_sorteo = int(df['sorteo'].iloc[-1])
    
    nueva_jugada = {
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_lanzamiento": "Próximo Sorteo",
        "sorteo_objetivo": ultimo_sorteo + 1,
        "juego": "LOTO3_TRICORE",
        "numeros": prediccion_final,
        "algoritmo": "Tri-Core (RF Independiente)",
        "score_afinidad": min(score_final, 99),  # AUDITORÍA v4: Eliminado +25 artificial
        "nota_especial": "ESTRUCTURA_POSICIONAL"
    }
    
    # 4. Inyectar en Dashboard
    guardar_en_dashboard(nueva_jugada)

def guardar_en_dashboard(jugada):
    """
    Guarda jugada en dashboard con ESCRITURA ATÓMICA.
    AUDITORÍA v4: Previene corrupción de JSON si el proceso muere durante escritura.
    """
    data = []
    if os.path.exists(RUTA_DASHBOARD):
        try:
            with open(RUTA_DASHBOARD, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Dashboard corrupto o vacío ({e}), creando uno nuevo.")
            data = []
        except IOError as e:
            logger.error(f"Error leyendo dashboard: {e}")
            data = []

    # Insertar al principio
    data.insert(0, jugada)
    data = data[:200]  # Buffer de memoria

    # ESCRITURA ATÓMICA: write-temp-rename pattern
    try:
        dir_name = os.path.dirname(RUTA_DASHBOARD)
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix='.json',
            dir=dir_name,
            delete=False
        ) as tmp_file:
            json.dump(data, tmp_file, indent=4, ensure_ascii=False)
            tmp_path = tmp_file.name

        # Rename atómico (en mismo filesystem)
        shutil.move(tmp_path, RUTA_DASHBOARD)
        logger.info(f"Predicción Tri-Core {jugada['numeros']} guardada exitosamente")
    except Exception as e:
        logger.error(f"Error escribiendo JSON: {e}")
        # Intentar limpiar archivo temporal si existe
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

if __name__ == "__main__":
    ejecutar_sistema_tricore()