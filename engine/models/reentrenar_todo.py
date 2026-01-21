import sys
import os
import logging

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Asegurar que podemos importar modulos hermanos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from oraculo_neural import OraculoNeural
except ImportError:
    # Fallback si se ejecuta desde otro directorio
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'models'))
    from oraculo_neural import OraculoNeural

def reentrenar_modelos_profundos(target_games=None):
    print("\n" + "="*60)
    print("🧠 REENTRENAMIENTO PROFUNDO: Actualizando Redes Neuronales")
    print("="*60)
    
    all_games = ["LOTO", "LOTO3", "LOTO4", "RACHA"]
    
    # Si se especifican juegos, filtramos. Si no, usamos todos (comportamiento legacy/manual)
    if target_games:
        juegos = [g for g in all_games if g in target_games]
        if not juegos:
            print("   ℹ️  No hay juegos nuevos para reentrenar. Saltando.")
            return
    else:
        juegos = all_games
        
    versiones = ["v3", "v4"]
    
    total_reentrenados = 0
    errores = 0
    
    for juego in juegos:
        for version in versiones:
            try:
                print(f"\n   ⚙️  Entrenando {juego} ({version})...")
                # Instanciar con force_retrain no es necesario porque llamaremos a entrenar() explícitamente
                oraculo = OraculoNeural(game_id=juego, version=version)
                
                # Forzamos entrenamiento
                metrics = oraculo.entrenar()
                
                if metrics:
                    print(f"      ✅ Éxito: Train={metrics.get('train_score',0):.3f}, Test={metrics.get('test_score',0):.3f}")
                    total_reentrenados += 1
                else:
                    print("      ⚠️  No se pudo entrenar (datos insuficientes o error interno).")
            except Exception as e:
                print(f"      ❌ Error crítico en {juego} {version}: {e}")
                errores += 1

    print(f"\n   🏁 Resumen: {total_reentrenados} modelos actualizados, {errores} fallos.")

if __name__ == "__main__":
    reentrenar_modelos_profundos()
