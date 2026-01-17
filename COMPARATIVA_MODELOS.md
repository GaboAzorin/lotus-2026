# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-17 22:20:09

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO3', 'oraculo_neural_v4') |                       12.941 |                       43.33 |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        5.161 |                       20    |                            31 |                  0.839 |
| ('LOTO4', 'oraculo_neural_v4') |                       20     |                       20    |                            31 |                  2     |
| ('RACHA', 'oraculo_neural_v3') |                       18.382 |                       40    |                            34 |                  5.118 |
| ('RACHA', 'oraculo_neural_v4') |                       15     |                       15    |                            34 |                  6     |

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
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |