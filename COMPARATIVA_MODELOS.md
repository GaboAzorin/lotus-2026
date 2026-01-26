# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-26 13:43:46

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        1.95  |                       40    |                           358 |                  1.109 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.69  |                        1.67 |                           339 |                  0.826 |
| ('LOTO3', 'oraculo_neural_v4') |                        4.088 |                        5    |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        3.776 |                       50    |                           339 |                  0.785 |
| ('LOTO4', 'oraculo_neural_v4') |                        6.509 |                       20    |                           338 |                  0.834 |
| ('RACHA', 'oraculo_neural_v3') |                       18.5   |                       75    |                           340 |                  5.024 |
| ('RACHA', 'oraculo_neural_v4') |                       16.897 |                       50    |                           340 |                  4.906 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10317 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10313 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10305 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10318 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10306 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |