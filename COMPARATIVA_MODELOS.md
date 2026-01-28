# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-28 12:39:22

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
| ('LOTO4', 'oraculo_neural_v3') |                        3.35  |                       50    |                           406 |                  0.749 |
| ('LOTO4', 'oraculo_neural_v4') |                        5.432 |                       20    |                           405 |                  0.741 |
| ('RACHA', 'oraculo_neural_v3') |                       18.477 |                       75    |                           407 |                  5.017 |
| ('RACHA', 'oraculo_neural_v4') |                       18.256 |                       75    |                           407 |                  4.99  |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10322 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10313 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |