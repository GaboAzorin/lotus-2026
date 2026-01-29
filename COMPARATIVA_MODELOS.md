# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-29 21:44:29

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        1.952 |                       40    |                           425 |                  1.094 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.576 |                        1.67 |                           406 |                  0.69  |
| ('LOTO3', 'oraculo_neural_v4') |                        4.088 |                        5    |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        3.297 |                       50    |                           461 |                  0.74  |
| ('LOTO4', 'oraculo_neural_v4') |                        6.652 |                       20    |                           460 |                  0.846 |
| ('RACHA', 'oraculo_neural_v3') |                       18.477 |                       75    |                           463 |                  5.015 |
| ('RACHA', 'oraculo_neural_v4') |                       19.654 |                       75    |                           463 |                  5.093 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10317 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10322 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |