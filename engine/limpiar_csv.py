import pandas as pd

# Cargar datos
df = pd.read_csv('C:/Users/Gabriel/Documents/Python/lotus-2026/data/LOTO3_MAESTRO.csv')

# Quedarse solo con los que tienen n1 válido
df_good = df[df['n1'].notna()].copy()

# Guardar
df_good.to_csv('C:/Users/Gabriel/Documents/Python/lotus-2026/data/LOTO3_MAESTRO.csv', index=False)

print(f'Guardado: {len(df_good)} filas')
print(f'Ultimo sorteo: {df_good["sorteo"].max()}')
