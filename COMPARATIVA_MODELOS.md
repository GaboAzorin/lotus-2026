# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-19 06:32:00

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        2.164 |                       15    |                           107 |                  1.196 |
| ('LOTO', 'oraculo_neural_v4')  |                        0     |                        0    |                           107 |                  0     |
| ('LOTO3', 'oraculo_neural_v4') |                       12.941 |                       43.33 |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        3.925 |                       20    |                           107 |                  0.841 |
| ('LOTO4', 'oraculo_neural_v4') |                       12.897 |                       20    |                           107 |                  1.299 |
| ('RACHA', 'oraculo_neural_v3') |                       18.224 |                       60    |                           107 |                  5.065 |
| ('RACHA', 'oraculo_neural_v4') |                       11.636 |                       15    |                           107 |                  5.664 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10303 |            60    |          8 |
| LOTO3   | oraculo_neural_v4 |             23999 |            43.33 |          2 |
| LOTO3   | oraculo_neural_v4 |             23999 |            43.33 |          2 |
| LOTO3   | oraculo_neural_v4 |             23999 |            43.33 |          2 |
| RACHA   | oraculo_neural_v3 |             10304 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |            40    |          3 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |            40    |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |            40    |          7 |