# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-02-02 06:57:23

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        1.794 |                       40    |                           489 |                  1.027 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.499 |                        1.67 |                           470 |                  0.598 |
| ('LOTO3', 'oraculo_neural_v4') |                        4.088 |                        5    |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        3.169 |                       50    |                           486 |                  0.72  |
| ('LOTO4', 'oraculo_neural_v4') |                        6.639 |                       20    |                           485 |                  0.87  |
| ('RACHA', 'oraculo_neural_v3') |                       18.558 |                       75    |                           489 |                  5.02  |
| ('RACHA', 'oraculo_neural_v4') |                       19.325 |                       75    |                           489 |                  5.07  |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10327 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10317 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10324 |               75 |          8 |