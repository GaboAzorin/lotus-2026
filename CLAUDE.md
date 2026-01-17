# LOTO-2026 - Mapa del Proyecto

Sistema de analisis estadistico y prediccion experimental para loterias chilenas.

---

## Estructura General

```
lotus-2026/
├── index.html              # Dashboard principal
├── laboratorio.html        # Laboratorio Multiverso (analisis avanzado)
├── lab2.html               # Semaforo de Inferencia (predicciones experimentales)
├── dashboard_data.json     # Datos para el dashboard (generado automaticamente)
├── requirements.txt        # Dependencias Python
├── css/                    # Estilos separados
├── js/                     # Scripts separados
├── data/                   # Datos CSV y JSON
├── engine/                 # Motor de prediccion (Python)
├── tests/                  # Tests automatizados
├── support/                # Scripts auxiliares y deprecated
└── prueba_otros_juegos/    # Exploracion de nuevos juegos
```

---

## Frontend (HTML/CSS/JS)

### HTMLs (Raiz)

| Archivo | Descripcion |
|---------|-------------|
| `index.html` | Dashboard principal. Muestra ultimo sorteo, generadores de numeros (Gaussiano y Forense), historial, metricas de desempeno y temporizador al proximo sorteo. |
| `laboratorio.html` | Laboratorio Multiverso. Analisis financiero detallado, graficos de rendimiento por algoritmo, explorador de simulaciones con filtros, comparativa entre LOTO/LOTO3/LOTO4/RACHA. |
| `lab2.html` | Semaforo de Inferencia. Muestra las predicciones experimentales con score de confianza visual (Top 10 por juego). |

### CSS (`/css`)

| Archivo | Descripcion |
|---------|-------------|
| `index.css` | Estilos del dashboard principal. Variables CSS, timer, generadores, tablas, swiper, footer. |
| `laboratorio.css` | Estilos del laboratorio. Pestanas multiverso, KPIs, graficos, filtros, tablas de datos. |
| `lab2.css` | Estilos del semaforo. Cards de prediccion, barra de confianza, animaciones. |

### JavaScript (`/js`)

| Archivo | Descripcion |
|---------|-------------|
| `index.js` | Logica del dashboard. Carga CSV con PapaParse, renderiza sorteos, generadores Gaussiano y Forense, temporizador, historial. |
| `laboratorio.js` | Logica del laboratorio. Carga multiple de CSVs, calculo de metricas financieras, graficos Chart.js, filtros, tablas agregadas. |
| `lab2.js` | Logica del semaforo. Carga `dashboard_data.json`, renderiza cards con score de confianza, parseo inteligente de numeros. |

---

## Datos (`/data`)

### CSVs Maestros (Historial Oficial)

| Archivo | Descripcion |
|---------|-------------|
| `LOTO_HISTORIAL_MAESTRO.csv` | Historial completo de sorteos LOTO. Columnas: sorteo, fecha, LOTO_n1-n6, comodin, premios, ganadores, pozos. |
| `LOTO3_MAESTRO.csv` | Historial LOTO 3. Columnas: sorteo, fecha, n1-n3, premios (exacta, trio, par, terminacion). |
| `LOTO4_MAESTRO.csv` | Historial LOTO 4. Columnas: sorteo, fecha, n1-n4, premios por puntos. |
| `RACHA_MAESTRO.csv` | Historial RACHA. Columnas: sorteo, fecha, n1-n10. |

### CSVs de Simulacion

| Archivo | Descripcion |
|---------|-------------|
| `LOTO_SIMULACIONES.csv` | Registro de todas las predicciones generadas. Columnas: fecha_hora, juego, algoritmo, numeros, sorteo_objetivo, estado (PENDIENTE/AUDITADO), aciertos, score. |
| `LOTO_JUGADAS.csv` | Registro de jugadas reales realizadas (para tracking financiero). |

### JSONs

| Archivo | Descripcion |
|---------|-------------|
| `loto_biometrics.json` | Pesos posicionales por numero y juego. Usado por el generador Forense. |
| `loto_genome.json` | "Genoma" del LOTO: frecuencias, patrones, deltas, mapas de calor. |
| `meta_learner_maps.json` | Mapas del Meta-Learner (optimizacion de algoritmos). |
| `optimizer_history.json` | Historial del auto-optimizador. |

---

## Engine - Motor de Prediccion (`/engine`)

### Configuracion

| Archivo | Descripcion |
|---------|-------------|
| `config.py` | **Configuracion centralizada**. Rutas, archivos, GAME_CONFIG por juego, reglas de premios, constantes. Importar siempre desde aqui. |

### Modelos (`/engine/models`)

| Archivo | Descripcion |
|---------|-------------|
| `bot_dreamer.py` | **Orquestador principal**. Ejecuta el ciclo completo: scraping, prediccion, auditoria. Genera `dashboard_data.json`. |
| `oraculo_neural.py` | **Predictor ML**. Usa RandomForest multi-output. Versiones v3 (reglamento) y v4 (fisica posicional). |
| `generador_biometrico.py` | **Predictor estadistico**. Genera numeros basados en frecuencias historicas ponderadas por posicion. |
| `juez_implacable.py` | **Auditor**. Compara predicciones con resultados reales, calcula aciertos y actualiza estados. |
| `entrenador_cognitivo.py` | Entrena y recalibra los modelos periodicamente. |
| `analizador_forense.py` | Analiza patrones y genera `loto_biometrics.json`. |
| `meta_learner.py` | Meta-aprendizaje: optimiza hiperparametros y pesos de algoritmos. |
| `auto_optimizer.py` | Optimizador automatico de configuraciones. |
| `loto3_tricore.py` | Predictor especializado para LOTO 3 (numeros posicionales 0-9). |
| `loto3_ultra.py` | **Sistema avanzado LOTO 3** con todas las mejoras: Markov orden 3, modelos por franja horaria, calibracion de probabilidades, ventanas adaptativas, analisis de ciclos y patrones. |
| `consolidar_laboratorio.py` | Consolida datos del laboratorio. |
| `test_oraculo.py` | Tests del oraculo neural. |

### Scrapers (`/engine/scrapers`)

| Archivo | Descripcion |
|---------|-------------|
| `scraper_maestro.py` | **Scraper principal**. Usa Playwright para extraer resultados desde la web oficial. |
| `loto_parser_v3.py` | Parser de datos crudos de LOTO. |
| `loto_parsers_mix.py` | Parsers para LOTO3, LOTO4, RACHA. |
| `reconstructor_temporal.py` | Reconstruye datos historicos faltantes. |
| `test_scrap_grok.py` | Tests de scraping. |

### Herramientas (`/engine/tools`)

| Archivo | Descripcion |
|---------|-------------|
| `comparar_modelos.py` | Compara rendimiento entre diferentes modelos/algoritmos. |
| `consolidar_cola.py` | Consolida predicciones en cola. |
| `reparador_historico.py` | Repara inconsistencias en datos historicos. |

---

## Tests (`/tests`)

| Archivo | Descripcion |
|---------|-------------|
| `conftest.py` | Configuracion de pytest y fixtures. |
| `test_config.py` | Tests de configuracion. |
| `test_entrenador_cognitivo.py` | Tests del entrenador. |
| `test_juez_implacable.py` | Tests del auditor. |
| `test_oraculo_neural.py` | Tests del predictor ML. |

---

## Support (`/support`)

### Deprecated (`/support/deprecated`)
Scripts antiguos ya no usados pero conservados como referencia.

### Tests (`/support/tests`)
Scripts auxiliares de testing.

---

## Archivos Raiz

| Archivo | Descripcion |
|---------|-------------|
| `dashboard_data.json` | JSON con predicciones activas para el frontend. Generado por `bot_dreamer.py`. |
| `requirements.txt` | Dependencias: pandas, numpy, scikit-learn, playwright, etc. |
| `COMPARATIVA_MODELOS.md` | Documentacion de comparativa entre modelos. |
| `project_errors.json` | Log de errores del proyecto. |

---

## Flujo de Datos

```
1. SCRAPING
   scraper_maestro.py --> LOTO_HISTORIAL_MAESTRO.csv (y otros)

2. ANALISIS
   analizador_forense.py --> loto_biometrics.json
   entrenador_cognitivo.py --> loto_genome.json

3. PREDICCION
   oraculo_neural.py ──┐
   generador_biometrico.py ──┼──> LOTO_SIMULACIONES.csv
   loto3_tricore.py ──┘

4. AUDITORIA
   juez_implacable.py --> Actualiza LOTO_SIMULACIONES.csv (estado, aciertos)

5. DASHBOARD
   bot_dreamer.py --> dashboard_data.json

6. FRONTEND
   index.html / laboratorio.html / lab2.html --> Visualizacion
```

---

## Comandos Utiles

```bash
# Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# Ejecutar ciclo completo
python engine/models/bot_dreamer.py

# Solo auditar predicciones
python engine/models/juez_implacable.py

# Reentrenar modelos
python engine/models/entrenador_cognitivo.py

# Actualizar biometrics
python engine/models/analizador_forense.py

# Ejecutar tests
pytest tests/
```

---

## Algoritmos Disponibles

| Algoritmo | Archivo | Descripcion |
|-----------|---------|-------------|
| `forense` / `Bio` | generador_biometrico.py | Frecuencias ponderadas por posicion fisica |
| `gauss` | index.js (frontend) | Distribucion gaussiana con filtros estadisticos |
| `delta` | generador_biometrico.py | Analisis de deltas entre sorteos |
| `markov` | generador_biometrico.py | Cadenas de Markov para transiciones |
| `oraculo_neural_v3` | oraculo_neural.py | RandomForest basado en reglamento |
| `oraculo_neural_v4` | oraculo_neural.py | RandomForest basado en fisica posicional |
| `consenso` | bot_dreamer.py | Votacion mayoritaria entre algoritmos |
| `loto3_ultra_ensemble` | loto3_ultra.py | Ensemble avanzado: Markov O3 + RF calibrado + frecuencias + patrones |

---

## Juegos Soportados

| Juego | Numeros | Rango | Tipo |
|-------|---------|-------|------|
| LOTO | 6 | 1-41 | SET (sin orden) |
| LOTO 3 | 3 | 0-9 | POSICIONAL (orden importa) |
| LOTO 4 | 4 | 1-25 | SET |
| RACHA | 10 | 1-20 | SET |

---

*Generado el 2026-01-17*
