# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-22 01:21:09

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        2.113 |                          15 |                           177 |                  1.209 |
| ('LOTO', 'oraculo_neural_v4')  |                        0     |                           0 |                           158 |                  0     |
| ('LOTO3', 'oraculo_neural_v4') |                        4.088 |                           5 |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        2.872 |                          20 |                           188 |                  0.702 |
| ('LOTO4', 'oraculo_neural_v4') |                        8.298 |                          20 |                           188 |                  0.862 |
| ('RACHA', 'oraculo_neural_v3') |                       18.413 |                          75 |                           189 |                  5.005 |
| ('RACHA', 'oraculo_neural_v4') |                       22.698 |                          50 |                           189 |                  5.439 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10306 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |