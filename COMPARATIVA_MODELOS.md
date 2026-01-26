# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-26 01:25:22

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        2.006 |                          15 |                           218 |                  1.17  |
| ('LOTO', 'oraculo_neural_v4')  |                        0     |                           0 |                           199 |                  0     |
| ('LOTO3', 'oraculo_neural_v4') |                        4.088 |                           5 |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        2.75  |                          20 |                           240 |                  0.7   |
| ('LOTO4', 'oraculo_neural_v4') |                        6.5   |                          20 |                           240 |                  0.708 |
| ('RACHA', 'oraculo_neural_v3') |                       18.527 |                          75 |                           241 |                  5.017 |
| ('RACHA', 'oraculo_neural_v4') |                       18.921 |                          50 |                           241 |                  5.104 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10313 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10313 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10306 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |