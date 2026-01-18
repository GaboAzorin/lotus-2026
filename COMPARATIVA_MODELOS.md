# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-18 18:21:46

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO3', 'oraculo_neural_v4') |                       12.941 |                       43.33 |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        4.419 |                       20    |                            86 |                  0.884 |
| ('LOTO4', 'oraculo_neural_v4') |                       11.395 |                       20    |                            86 |                  1.14  |
| ('RACHA', 'oraculo_neural_v3') |                       16.538 |                       40    |                            52 |                  5.135 |
| ('RACHA', 'oraculo_neural_v4') |                       11.538 |                       15    |                            52 |                  5.654 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23999 |            43.33 |          2 |
| LOTO3   | oraculo_neural_v4 |             23999 |            43.33 |          2 |
| LOTO3   | oraculo_neural_v4 |             23999 |            43.33 |          2 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          3 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          3 |
| RACHA   | oraculo_neural_v3 |             10302 |            40    |          3 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |