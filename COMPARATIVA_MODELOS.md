# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-24 12:32:01

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
| ('LOTO4', 'oraculo_neural_v3') |                        2.768 |                          20 |                           224 |                  0.701 |
| ('LOTO4', 'oraculo_neural_v4') |                        6.964 |                          20 |                           224 |                  0.723 |
| ('RACHA', 'oraculo_neural_v3') |                       18.7   |                          75 |                           227 |                  5.026 |
| ('RACHA', 'oraculo_neural_v4') |                       20.088 |                          50 |                           227 |                  5.233 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10313 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10310 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10311 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |