import pandas as pd
import os

base = 'C:/Users/Gabriel/Documents/Python/lotus-2026/data'

# LOTO
df = pd.read_csv(os.path.join(base, 'LOTO_HISTORIAL_MAESTRO.csv'))
ult = df.tail(1).iloc[0]
print('=== LOTO ===')
print(f"Sorteo #{ult['sorteo']} - {ult['fecha']}")
print(f"Numeros: {ult['LOTO_n1']}, {ult['LOTO_n2']}, {ult['LOTO_n3']}, {ult['LOTO_n4']}, {ult['LOTO_n5']}, {ult['LOTO_n6']}")
print()

# LOTO3
df = pd.read_csv(os.path.join(base, 'LOTO3_MAESTRO.csv'))
print('=== LOTO3 (ultimos 3) ===')
for _, row in df.tail(3).iterrows():
    print(f"#{row['sorteo']} - {row['fecha'][:10]} {row['hora']}h: {row['n1']}-{row['n2']}-{row['n3']}")
print()

# LOTO4
df = pd.read_csv(os.path.join(base, 'LOTO4_MAESTRO.csv'))
print('=== LOTO4 (ultimos 3) ===')
for _, row in df.tail(3).iterrows():
    print(f"#{row['sorteo']} - {row['fecha'][:10]} {row['hora']}h: {row['n1']}-{row['n2']}-{row['n3']}-{row['n4']}")
print()

# RACHA
df = pd.read_csv(os.path.join(base, 'RACHA_MAESTRO.csv'))
print('=== RACHA (ultimos 3) ===')
for _, row in df.tail(3).iterrows():
    nums = f"{row['n1']}-{row['n2']}-{row['n3']}-{row['n4']}-{row['n5']}-{row['n6']}-{row['n7']}-{row['n8']}-{row['n9']}-{row['n10']}"
    print(f"#{row['sorteo']} - {row['fecha'][:10]} {row['hora']}h: {nums}")
