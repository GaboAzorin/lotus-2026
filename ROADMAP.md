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
- [ ] **[IMP-AUD-001] Corregir Scoring RACHA**: Eliminar la curva en V invertida que asigna 100% de éxito a 0 aciertos. Implementar curva monótona.
- [ ] **[ERR-005] Consenso Robusto**: Asegurar que el loop de consenso en `bot_dreamer.py` no termine prematuramente con muestras insuficientes (<5).
- [ ] **[ERR-006] Fix IndexError en Ventanas Pequeñas**: Validar tamaño de dataset en `oraculo_neural.py` antes de acceder a índices negativos.

### 🟡 Calidad de Datos
- [ ] **[ERR-007] Robustez de Scraper**: Aumentar timeout en `scraper_maestro.py` y manejar esperas explícitas para conexiones lentas.
- [ ] **[IMP-DATA-003] Backups Automáticos**: Implementar copia `.bak` antes de que `juez_implacable.py` modifique `SIMULACIONES.csv`.

---

## 🚀 Fase 2: Optimización de Inteligencia Artificial (Semana 3-4)
*Objetivo: Mejorar la precisión predictiva y reducir el overfitting detectado.*

### 🟡 Mejoras de Modelado (ML)
- [ ] **[IMP-ML-001] Reducir Overfitting en Random Forest**: Ajustar hiperparámetros (`max_depth=5`, `min_samples_leaf=20`) en `oraculo_neural.py`.
- [ ] **[IMP-ML-003] Optimización de Hiperparámetros**: Implementar `GridSearchCV` con `TimeSeriesSplit` para encontrar la configuración óptima automáticamente.
- [ ] **[IMP-ML-002] Explorar Gradient Boosting**: Integrar XGBoost o LightGBM como alternativas a Random Forest y comparar rendimiento.

### 🔵 Ingeniería de Características (Feature Engineering)
- [ ] **[IMP-FEAT-001] Análisis de Rachas**: Crear features para detectar números "calientes" (frecuentes recientes) y "fríos".
- [ ] **[IMP-FEAT-003] Correlación Posicional**: Analizar si el valor de una bola influye en la paridad o terminación de la siguiente.

### 🔵 Validación
- [ ] **[IMP-ML-008] Validación Cruzada Temporal**: Implementar `TimeSeriesSplit` (5 folds) en lugar de un simple split 80/20 para métricas más realistas.

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
