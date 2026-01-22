import os
import json
import glob
import pandas as pd

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', '..', 'data'))
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
CSV_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
OUTPUT_FILE = os.path.normpath(os.path.join(BASE_DIR, '..', '..', 'dashboard_data.json'))

def ejecutar_consolidacion_hibrida():
    print("🔄 Limpiando y Actualizando Dashboard...")
    todas_las_predicciones = []
    ids_vistos = set()

    # 1. Cargar desde CSV
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                # --- EL FIX CRÍTICO AQUÍ ---
                # Reemplazamos NaN por None (Python None -> JSON null)
                df = df.where(pd.notnull(df), None)
                
                # Cargamos PENDIENTES y AUDITADOS recientes para mantener historial
                # Si el usuario quiere ver "cómo nos fue", necesitamos los auditados.
                registros = df[df['estado'].isin(['PENDIENTE', 'AUDITADO'])].to_dict(orient='records')
                
                # Opcional: Limitar historial de auditados para no explotar el JSON
                # Por ahora traemos todo lo del CSV (asumiendo que Juez limpia o rota logs antiguos si crece mucho)
                
                for p in registros:
                    todas_las_predicciones.append(p)
                    ids_vistos.add(str(p['id']))
        except Exception as e:
            print(f"   ⚠️ Error en CSV: {e}")

    # 2. Cargar desde Queue (archivos JSON individuales)
    archivos_json = glob.glob(os.path.join(QUEUE_DIR, "prediccion_*.json"))
    for archi in archivos_json:
        try:
            with open(archi, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Sanitizar el objeto individual de forma robusta
                sanitized_data = {}
                for k, v in data.items():
                    if isinstance(v, list):
                        sanitized_data[k] = v
                    elif v is None:
                        sanitized_data[k] = None
                    elif pd.isna(v):
                         sanitized_data[k] = None
                    else:
                        sanitized_data[k] = v
                
                if str(sanitized_data.get('id')) not in ids_vistos:
                    todas_las_predicciones.append(sanitized_data)
                    ids_vistos.add(str(sanitized_data.get('id')))
        except Exception as e:
            print(f"   ⚠️ Error en JSON {archi}: {e}")

    # 3. Guardado final (Limpio de NaN)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # allow_nan=False lanzaría un error si se nos escapa un NaN, 
        # lo cual es bueno para debuggear.
        json.dump(todas_las_predicciones, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Dashboard saneado con {len(todas_las_predicciones)} registros.")

if __name__ == "__main__":
    ejecutar_consolidacion_hibrida()