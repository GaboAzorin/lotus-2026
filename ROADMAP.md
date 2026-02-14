# 🗺️ Roadmap: Proyecto Lotus-2026

> **Última actualización:** 2026-02-14
> **Branch actual:** `telegram-bot`
> **Estado:** En desarrollo activo

> **Leyenda de Prioridad:**
> - 🔴 **CRÍTICO:** Bloqueante o riesgo alto
> - 🟡 **ALTO:** Funcionalidad core
> - 🔵 **MEDIO:** Mejoras arquitectura/UX
> - ⚪ **BAJO:** Ideas experimentales

---

## 🚀 Fase Actual: Telegram Bot y Automatización (Febrero 2026)

### 🔴 En Progreso
- [ ] **[TELEGRAM-001] Bot interactivo**: Comando `/predicciones`, `/status`, `/resultados`
- [ ] **[TELEGRAM-002] Integración con crons**: Scraping y predictions automatizados
- [ ] **[TELEGRAM-003] Notificacionespush**: Alertas de nuevos sorteos y resultados

### 🟡 Pendiente
- [ ] **[TELEGRAM-004] Historial de predicciones**: Ver predicciones anteriores via bot
- [ ] **[TELEGRAM-005] Comandos de configuración**: Cambiar preferencias de notificación

---

## 📊 Fase 1: Estabilización (Completada)

### ✅ Done
- [x] Fix Race Condition en `consolidar_cola.py`
- [x] Sanitización de Inputs en `juez_implacable.py`
- [x] Validación de Oráculo
- [x] Fix NaN Handling en `consolidar_laboratorio.py`
- [x] Scoring RACHA corregido
- [x] Consenso Robusto en `bot_dreamer.py`
- [x] Backups automáticos (.bak)

---

## 🤖 Fase 2: Machine Learning (En Progreso)

### 🟡 Pendiente
- [ ] **[ML-001] Reducir Overfitting**: Ajustar `max_depth=5`, `min_samples_leaf=20`
- [ ] **[ML-002] GridSearchCV con TimeSeriesSplit**
- [ ] **[ML-003] Integrar XGBoost/LightGBM** como alternativa a RandomForest

### 🔵 Pendiente
- [ ] **[FEAT-001] Vector de Gaps (Recencia)**: Feature crítico para预测
- [ ] **[FEAT-002] Deltas y Velocidad**: Diferencia promedio entre sorteos
- [ ] **[FEAT-003] Meta-Features**: Inyectar paridad, suma, terminaciones

---

## 🎯 Fase 3: Estrategia RACHA (Pendiente)

### 🔴 Pendiente
- [ ] **[RACHA-001] Transformar a clasificación binaria**: 20 filas por sorteo (una por bola)
- [ ] **[RACHA-002] Selección negativa**: Identificar bolas que NO saldrán

---

## 📈 Fase 4: Métricas y Validación (Pendiente)

### 🔴 Pendiente
- [ ] **[VAL-001] Implementar "Hit Rate @ K"**: Métrica real de éxito
- [ ] **[VAL-002] Optimizar para Top-K**: No accuracy binario

---

## 🛠️ Fase 5: Arquitectura y Mantenibilidad

### 🔵 Pendiente
- [ ] **[ARCH-001] Centralización de Config**: Todo en `config.py`
- [ ] **[ARCH-002] Unificación de Parsers**: Un solo módulo robusto
- [ ] **[ARCH-003] Estandarización de Logging**: Eliminar `print()`, usar `logging`

### ⚪ Pendiente
- [ ] **[PERF-001] Optimización Forense**: Reducir loops de 5000 a ~200 intentos
- [ ] **[PERF-002] Caché Local**: `localStorage` en frontend

---

## 🔮 Fase 6: Futuro

### ⚪ Ideas
- [ ] Stacking Ensemble (RF + XGBoost + modelos estadísticos)
- [ ] Embeddings de Combinaciones (Word2Vec)
- [ ] Migración a SQLite/PostgreSQL
- [ ] Modo Oscuro y Vista Móvil

---

## 📋 Archivos del Proyecto

```
lotus-2026/
├── engine/
│   ├── config.py                    # ✅ Centralizado
│   ├── telegram_config.py            # ✅ Config del bot
│   ├── telegram_notifier.py          # ✅ Notificaciones
│   ├── loto_orquestador.py           # 🆕 Orquestador principal
│   ├── debug_keys.py                 # 🆕 Debug
│   ├── limpiar_csv.py                 # 🆕 Limpieza datos
│   ├── models/
│   │   ├── bot_dreamer.py            # Orquestador ML
│   │   ├── oraculo_neural.py         # RandomForest
│   │   ├── generador_biometrico.py    # Estadistico
│   │   ├── loto3_ultra.py            # LOTO3 avanzado
│   │   └── ...
│   └── scrapers/
│       ├── scraper_maestro.py        # Playwright
│       └── ...
├── data/
│   ├── LOTO_HISTORIAL_MAESTRO.csv    # Historia LOTO
│   ├── LOTO3_MAESTRO.csv             # Historia LOTO3
│   ├── LOTO4_MAESTRO.csv             # Historia LOTO4
│   ├── RACHA_MAESTRO.csv             # Historia RACHA
│   └── LOTO_SIMULACIONES.csv         # Predicciones
├── index.html                        # Dashboard principal
├── laboratorio.html                  # Analisis financiero
└── lab2.html                         # Predicciones experimentales
```

---

## 🎯 Próximo Paso Sugerido

**Terminar integración Telegram Bot** → luego continuar con ML y features de Recencia.
