# 🗺️ Roadmap: Proyecto Lotus-2026

Este documento detalla la hoja de ruta estratégica para el desarrollo y estabilización del proyecto, integrando correcciones de errores críticos y mejoras evolutivas.

> **Leyenda de Prioridad:**
> - 🔴 **CRÍTICO:** Debe resolverse de inmediato (bloqueante o riesgo alto).
> - 🟡 **ALTO:** Importante para la funcionalidad y precisión core.
> - 🔵 **MEDIO:** Mejoras de arquitectura, UX o rendimiento.
> - ⚪ **BAJO/FUTURO:** Ideas experimentales o mejoras menores.

---

## 🏗️ Fase 1: Estabilización y Corrección de Errores (Semana 1-2)
*Objetivo: Eliminar bugs críticos, asegurar la integridad de datos y prevenir fallos silenciosos.*

### 🔴 Seguridad y Estabilidad
- [x] **[ERR-001] Fix Race Condition en `consolidar_cola.py`**: Reemplazar loop infinito inseguro por `threading.Lock` o `portalocker` para evitar deadlocks.
- [x] **[ERR-003] Sanitización de Inputs**: Reemplazar `ast.literal_eval()` por `json.loads()` en `juez_implacable.py` para prevenir inyección de código.
- [x] **[ERR-002] Validación de Oráculo**: Asegurar que `OraculoNeural` tenga método `predecir()` antes de invocarlo para evitar fallos silenciosos.
- [x] **[ERR-004] Fix NaN Handling**: Reemplazar condición frágil `v == v` por `pd.isna()` en `consolidar_laboratorio.py`.

### 🔴 Lógica de Negocio Core
- [x] **[IMP-AUD-001] Corregir Scoring RACHA**: Eliminar la curva en V invertida que asigna 100% de éxito a 0 aciertos. Implementar curva monótona.
- [x] **[ERR-005] Consenso Robusto**: Asegurar que el loop de consenso en `bot_dreamer.py` no termine prematuramente con muestras insuficientes (<5).
- [x] **[ERR-006] Fix IndexError en Ventanas Pequeñas**: Validar tamaño de dataset en `oraculo_neural.py` antes de acceder a índices negativos.

### 🟡 Calidad de Datos
- [x] **[ERR-007] Robustez de Scraper**: Aumentar timeout en `scraper_maestro.py` y manejar esperas explícitas para conexiones lentas.
- [x] **[IMP-DATA-003] Backups Automáticos**: Implementar copia `.bak` antes de que `juez_implacable.py` modifique `SIMULACIONES.csv`.
- [x] **[FIX-PIPE-001] Filtrado de Pipeline IA**: Asegurar que solo los juegos con nuevos sorteos activen el reentrenamiento y optimización.

---

## 🚀 Fase 2: Optimización de Inteligencia Artificial (Semana 3-4)
*Objetivo: Mejorar la precisión predictiva y reducir el overfitting detectado.*

### 🟡 Mejoras de Modelado (ML)
- [x] **[IMP-ML-001] Reducir Overfitting en Random Forest**: Ajustar hiperparámetros (`max_depth=5`, `min_samples_leaf=20`) en `oraculo_neural.py`.
- [x] **[IMP-ML-003] Optimización de Hiperparámetros**: Implementar `GridSearchCV` con `TimeSeriesSplit` para encontrar la configuración óptima automáticamente.
- [x] **[IMP-ML-002] Explorar Gradient Boosting**: Integrar XGBoost o LightGBM como alternativas a Random Forest y comparar rendimiento.

### 🔵 Ingeniería de Características (Feature Engineering)
- [x] **[IMP-FEAT-001] Análisis de Rachas**: Crear features para detectar números "calientes" (frecuentes recientes) y "fríos".
- [x] **[IMP-FEAT-003] Correlación Posicional**: Analizar si el valor de una bola influye en la paridad o terminación de la siguiente.

### 🔵 Validación
- [x] **[IMP-ML-008] Validación Cruzada Temporal**: Implementar `TimeSeriesSplit` (5 folds) en lugar de un simple split 80/20 para métricas más realistas.

---

## 🧠 Fase 2.5: Ingeniería de Características Avanzada - El Eslabón Perdido
*Objetivo: Transformar el modelo de "números crudos" a características que capturen la física del sorteo.*

### 🔴 Variables de Recencia (Gaps) - CRÍTICO
- [x] **[IMP-FEAT-004] Vector de Gaps (Recencia)**: Crear un vector de tamaño 41 (LOTO) donde cada posición sea el `lag` actual de ese número ("hace cuántos sorteos no sale el 5"). Esta es la variable más predictiva en sistemas mecánicos (ley del retorno a la media).
- [x] **[IMP-FEAT-005] Inyectar Gaps en OraculoNeural**: Añadir el vector de `Gaps` (Recencia) a `input_features` en `_preparar_dataset`.

### 🟡 Deltas y Velocidad
- [x] **[IMP-FEAT-006] Deltas Promedio**: Calcular la diferencia promedio entre los números de los últimos 3 sorteos como feature adicional.

### 🟡 Meta-Features del Biométrico
- [x] **[IMP-FEAT-007] Inyectar Meta-Features**: El `generador_biometrico.py` calcula paridad y terminaciones pero no las pasa al modelo. Inyectar `paridad_promedio`, `suma_total`, y `terminacion_mas_frecuente` de la ventana anterior como columnas en X.

---

## 🎯 Fase 2.6: Estrategia RACHA - Inversión del Problema (Negative Selection)
*Objetivo: Cambiar el enfoque de "predecir ganadores" a "descartar perdedores".*

El modelo `MultiOutputClassifier` para RACHA (20 números, elegir 10) está condenado al 50% (azar puro) porque intenta minimizar el error cuadrático medio, lo que lo lleva a predecir siempre el promedio.

### 🔴 Cambio de Arquitectura
- [x] **[IMP-RACHA-001] Clasificación Binaria por Número**: Transformar el dataset de 1 fila por sorteo a **20 filas por sorteo** (una por cada bola posible).
  - *Features*: Recencia de la bola, Frecuencia en los últimos 10/50/100 sorteos, ¿Salió en el sorteo anterior?
  - *Target*: `1` (Salió) o `0` (No salió).
- [x] **[IMP-RACHA-002] Estrategia de Selección Negativa**: Entrenar al modelo para encontrar los **0s más seguros** (números que *seguro* no saldrán) y descartarlos. Es matemáticamente más fácil identificar una "bola fría" que una "bola caliente".

---

## ⚙️ Fase 2.7: Ajuste de Hiperparámetros y Modelo
*Objetivo: Escapar del underfitting causado por configuración demasiado conservadora.*

Tu GridSearch actual es demasiado conservador (`max_depth: 3-8`). Estás induciendo *underfitting* (sesgo alto) para evitar el *overfitting*.

### 🟡 Migración a XGBoost/LightGBM
- [x] **[IMP-ML-009] Activar XGBoost en `_build_model`**: Veo el `try/import` en tu código, pero el `_build_model` fuerza `RandomForest`. XGBoost maneja mejor los datos tabulares desbalanceados y valores nulos.
- [x] **[IMP-ML-010] Configurar XGBClassifier para RACHA**: Usar `objective='binary:logistic'` para la estrategia de RACHA transformada.

### 🔵 Función de Objetivo Personalizada
- [x] **[IMP-ML-011] Métrica de Distancia Numérica**: El Random Forest optimiza "Accuracy" o "Gini". En lotería, fallar por 1 número (sacar 40 cuando salió 41) es un fallo total para el modelo, pero un "casi acierto" para la física. Definir una métrica de evaluación que penalice menos los errores cercanos (distancia numérica). *Implementado via `logloss` en XGBoost que penaliza proporcionalmente a la confianza del error.*

---

## 📊 Fase 2.8: Validación - La Ilusión del "Accuracy"
*Objetivo: Implementar métricas que reflejen el valor real del modelo.*

Los logs muestran `Test Accuracy: 0.000` o `0.1041`. Esto es engañoso. En un espacio de (41 choose 6) combinaciones, el accuracy exacto siempre será cercano a 0.

### 🔴 Nueva Métrica de Éxito
- [x] **[IMP-VAL-001] Implementar "Hit Rate @ K"**: De los 10 números que tu modelo predijo con mayor probabilidad (usando `predict_proba`), ¿cuántos estaban realmente en el sorteo ganador?
- [x] **[IMP-VAL-002] Optimizar para Top-K**: Si tu modelo consistentemente mete 1 o 2 números ganadores en su Top 10 de probabilidades, ya tienes una ventaja sobre el azar. Optimiza para maximizar esa métrica, no el accuracy binario.

### 🟡 Validación de Scraper
- [x] **[IMP-VAL-003] Validación de Esquema JSON en Scraper**: Añadir validación de esquema JSON. Si `results` está vacío, no guardar nada y lanzar error explícito para no entrenar con ceros.

---

## 🛠️ Fase 3: Arquitectura y Mantenibilidad (Mes 2)
*Objetivo: Pagar deuda técnica y preparar el sistema para escalar.*

### 🔵 Refactorización
- [ ] **[ERR-010] Centralización de Configuración**: Mover todas las constantes (HORARIOS, GAME_CONFIG) a `config.py` y eliminar duplicados.
- [ ] **[ERR-013] Unificación de Parsers**: Consolidar `loto_parser_v3.py` y `loto_parsers_mix.py` en un módulo único y robusto.
- [ ] **[ERR-017] Estandarización de Logging**: Reemplazar todos los `print()` dispersos por un sistema de `logging` estructurado y rotativo.

### 🔵 Rendimiento
- [ ] **[ERR-011] Optimización Forense**: Reducir el loop de intentos en `predict_smart_gaussian` (de 5000 a ~200) para acelerar predicciones.

---

## 🔮 Fase 4: Expansión y Futuro (Mes 3+)
*Objetivo: Nuevas capacidades y mejoras de experiencia de usuario.*

### ⚪ Frontend y UX
- [ ] **[IMP-FE-001] Caché Local**: Implementar `localStorage` para CSVs en el frontend y reducir carga inicial.
- [ ] **Modo Oscuro Nativo**: Mejorar la experiencia visual en entornos con poca luz.
- [ ] **Vista Móvil**: Optimizar tablas y gráficos para pantallas pequeñas.

### ⚪ I+D (Investigación y Desarrollo)
- [ ] **[IMP-ML-004] Stacking Ensemble**: Crear un súper-modelo que combine las predicciones de RF, XGBoost y modelos estadísticos.
- [ ] **[IMP-FEAT-002] Embeddings de Combinaciones**: Experimentar con Word2Vec para encontrar relaciones semánticas entre jugadas históricas.
- [ ] **Migración a SQL**: Mover de CSV a SQLite/PostgreSQL para manejo eficiente de millones de registros.
