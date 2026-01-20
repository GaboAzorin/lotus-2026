# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-20 06:29:36

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
| ('LOTO4', 'oraculo_neural_v3') |                        3.117 |                       20    |                           154 |                  0.734 |
| ('LOTO4', 'oraculo_neural_v4') |                        8.961 |                       20    |                           154 |                  0.909 |
| ('RACHA', 'oraculo_neural_v3') |                       19.318 |                       75    |                           154 |                  5.071 |
| ('RACHA', 'oraculo_neural_v4') |                       23.766 |                       30    |                           154 |                  5.513 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10305 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10305 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |