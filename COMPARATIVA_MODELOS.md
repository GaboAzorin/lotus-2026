# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-28 01:20:25

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
| ('LOTO4', 'oraculo_neural_v3') |                        3.469 |                       50    |                           392 |                  0.76  |
| ('LOTO4', 'oraculo_neural_v4') |                        5.627 |                       20    |                           391 |                  0.767 |
| ('RACHA', 'oraculo_neural_v3') |                       18.384 |                       75    |                           393 |                  5.013 |
| ('RACHA', 'oraculo_neural_v4') |                       17.837 |                       75    |                           393 |                  4.954 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10313 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10320 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |