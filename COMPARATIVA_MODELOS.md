# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-21 06:29:46

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        2.113 |                       15    |                           177 |                  1.209 |
| ('LOTO', 'oraculo_neural_v4')  |                        0     |                        0    |                           158 |                  0     |
| ('LOTO3', 'oraculo_neural_v4') |                       12.941 |                       43.33 |                            34 |                  1.088 |
| ('LOTO4', 'oraculo_neural_v3') |                        3.038 |                       20    |                           158 |                  0.728 |
| ('LOTO4', 'oraculo_neural_v4') |                        8.734 |                       20    |                           158 |                  0.905 |
| ('RACHA', 'oraculo_neural_v3') |                       19.119 |                       75    |                           159 |                  5.057 |
| ('RACHA', 'oraculo_neural_v4') |                       24.308 |                       50    |                           159 |                  5.541 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10303 |               75 |          8 |
| RACHA   | oraculo_neural_v4 |             10307 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10301 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10303 |               50 |          7 |
| RACHA   | oraculo_neural_v3 |             10304 |               50 |          7 |