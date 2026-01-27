# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-27 01:24:22

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
| ('LOTO4', 'oraculo_neural_v3') |                        3.733 |                       50    |                           359 |                  0.777 |
| ('LOTO4', 'oraculo_neural_v4') |                        6.145 |                       20    |                           358 |                  0.788 |
| ('RACHA', 'oraculo_neural_v3') |                       18.329 |                       75    |                           362 |                  5.003 |
| ('RACHA', 'oraculo_neural_v4') |                       16.202 |                       50    |                           362 |                  4.854 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10313 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10317 |               75 |          8 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10311 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| LOTO4   | oraculo_neural_v3 |             11585 |               50 |          3 |
| RACHA   | oraculo_neural_v3 |             10310 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |