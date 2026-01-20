import os
import json
import pandas as pd
import sys
import glob
import logging
import tempfile
import shutil
import time

# File locking: fcntl para Unix, msvcrt para Windows
if sys.platform == 'win32':
    import msvcrt
    fcntl = None
else:
    import fcntl
    msvcrt = None

# Configurar logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 1. Configuración de Rutas Relativas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', '..', 'data'))
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
CSV_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
LOCK_FILE = os.path.join(DATA_DIR, ".consolidar_cola.lock")

# 2. Inyección de rutas para encontrar el módulo 'models'
MODELS_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'models'))
if MODELS_DIR not in sys.path:
    sys.path.append(MODELS_DIR)


class FileLock:
    """
    Mutex basado en archivo para prevenir race conditions.
    AUDITORÍA v4: Previene conflictos entre Soñador y Juez.
    """
    def __init__(self, lock_file, timeout=120):
        self.lock_file = lock_file
        self.timeout = timeout
        self.fd = None

    def acquire(self):
        """Adquiere el lock con timeout."""
        start_time = time.time()
        while True:
            try:
                # Usamos 'a' (append) para no truncar el archivo cada vez.
                # 'a' crea el archivo si no existe.
                self.fd = open(self.lock_file, 'a')
                
                if sys.platform == 'win32':
                    import msvcrt
                    # LK_NBLCK: Non-blocking lock. Si falla, lanza IOError.
                    # Lock de 1 byte es suficiente.
                    msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Si llegamos aquí, tenemos el lock.
                return True
                
            except (IOError, OSError, PermissionError):
                # Puede fallar al abrir (PermissionError en Windows si tiene lock exclusivo)
                # o al hacer locking (IOError).
                if self.fd:
                    try:
                        self.fd.close()
                    except:
                        pass
                    self.fd = None
                
                if time.time() - start_time > self.timeout:
                    logger.warning(f"Timeout adquiriendo lock después de {self.timeout}s")
                    return False
                time.sleep(0.1)

    def release(self):
        """Libera el lock."""
        if self.fd:
            try:
                if sys.platform == 'win32':
                    import msvcrt
                    msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass
            finally:
                self.fd.close()
                self.fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

def consolidar():
    """
    Consolida predicciones de la cola al CSV maestro.
    AUDITORÍA v4: Usa mutex para prevenir race conditions.
    """
    logger.info("INICIANDO CONSOLIDACIÓN DE COLA Y LIMPIEZA...")

    # AUDITORÍA v4: Adquirir lock antes de procesar (timeout extendido a 120s)
    lock = FileLock(LOCK_FILE, timeout=120)
    if not lock.acquire():
        logger.error("No se pudo adquirir lock. Otro proceso está consolidando.")
        return

    try:
        # 3. Buscar archivos JSON en la cola
        pattern = os.path.join(QUEUE_DIR, "prediccion_*.json")
        ticket_files = glob.glob(pattern)

        if not ticket_files:
            logger.info("La cola está vacía. Nada que procesar.")
            return

        logger.info(f"Encontrados {len(ticket_files)} tickets nuevos.")

        # 4. Leer todos los tickets de la carpeta /queue
        nuevas_filas = []
        procesados = []

        for tf in ticket_files:
            try:
                with open(tf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    nuevas_filas.append(data)
                    procesados.append(tf)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON corrupto en {tf}: {e}")
            except IOError as e:
                logger.error(f"Error leyendo {tf}: {e}")

        if not nuevas_filas:
            return

        # 5. Cargar CSV Maestro existente o crear uno nuevo
        if os.path.exists(CSV_FILE):
            try:
                df_maestro = pd.read_csv(CSV_FILE)
            except Exception as e:
                logger.warning(f"Error leyendo CSV maestro: {e}. Creando nuevo.")
                df_maestro = pd.DataFrame()
        else:
            df_maestro = pd.DataFrame()

        # 6. Concatenar y asegurar que no haya duplicados por ID
        df_nuevos = pd.DataFrame(nuevas_filas)

        cols_orden = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo',
                      'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']

        for c in cols_orden:
            if c not in df_nuevos.columns:
                df_nuevos[c] = 0
            if c not in df_maestro.columns and not df_maestro.empty:
                df_maestro[c] = 0

        df_final = pd.concat([df_maestro, df_nuevos], ignore_index=True)
        df_final.drop_duplicates(subset=['id'], keep='last', inplace=True)

        # 7. AUDITORÍA v4: Guardar CSV con escritura atómica
        tmp_path = None
        try:
            dir_name = os.path.dirname(CSV_FILE)
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                suffix='.csv',
                dir=dir_name,
                delete=False,
                newline=''
            ) as tmp_file:
                df_final.to_csv(tmp_file, index=False)
                tmp_path = tmp_file.name
            shutil.move(tmp_path, CSV_FILE)
            logger.info(f"CSV Actualizado. Total registros: {len(df_final)}")
        except Exception as e:
            logger.error(f"Error guardando CSV: {e}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return

        # 8. Borrar archivos procesados de la cola
        for tf in procesados:
            try:
                os.remove(tf)
            except OSError as e:
                logger.warning(f"No se pudo borrar {tf}: {e}")

        # 9. Notificar al laboratorio
        logger.info("Notificando al laboratorio para refrescar dashboard...")
        try:
            from consolidar_laboratorio import ejecutar_consolidacion_hibrida
            ejecutar_consolidacion_hibrida()
        except ImportError:
            logger.warning("consolidar_laboratorio no disponible")
        except Exception as e:
            logger.warning(f"No se pudo actualizar dashboard: {e}")

        logger.info("CONSOLIDACIÓN Y LIMPIEZA FINALIZADA.")

    finally:
        # Siempre liberar el lock
        lock.release()

if __name__ == "__main__":
    consolidar()