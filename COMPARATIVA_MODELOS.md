# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-21 21:34:47

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
| ('LOTO4', 'oraculo_neural_v3') |                        2.793 |                          20 |                           179 |                  0.698 |
| ('LOTO4', 'oraculo_neural_v4') |                        7.709 |                          20 |                           179 |                  0.804 |
| ('RACHA', 'oraculo_neural_v3') |                       18.389 |                          75 |                           180 |                  5     |
| ('RACHA', 'oraculo_neural_v4') |                       23.306 |                          50 |                           180 |                  5.483 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |