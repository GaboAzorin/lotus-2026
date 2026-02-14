import pandas as pd
import os

base = 'C:/Users/Gabriel/Documents/Python/lotus-2026/data'

# LOTO
print("=== LOTO ===")
df = pd.read_csv(os.path.join(base, 'LOTO_HISTORIAL_MAESTRO.csv'))
print(f"Total: {len(df)}, con n1: {df['LOTO_n1'].notna().sum()}")
if df['LOTO_n1'].notna().sum() < len(df):
    df_good = df[df['LOTO_n1'].notna()].copy()
    df_good.to_csv(os.path.join(base, 'LOTO_HISTORIAL_MAESTRO.csv'), index=False)
    print(f"Limpio: {len(df_good)} filas, ultimo: {df_good['sorteo'].max()}")

# LOTO4
print("=== LOTO4 ===")
df = pd.read_csv(os.path.join(base, 'LOTO4_MAESTRO.csv'))
print(f"Total: {len(df)}, con n1: {df['n1'].notna().sum()}")
if df['n1'].notna().sum() < len(df):
    df_good = df[df['n1'].notna()].copy()
    df_good.to_csv(os.path.join(base, 'LOTO4_MAESTRO.csv'), index=False)
    print(f"Limpio: {len(df_good)} filas, ultimo: {df_good['sorteo'].max()}")

# RACHA
print("=== RACHA ===")
df = pd.read_csv(os.path.join(base, 'RACHA_MAESTRO.csv'))
print(f"Total: {len(df)}, con n1: {df['n1'].notna().sum()}")
if df['n1'].notna().sum() < len(df):
    df_good = df[df['n1'].notna()].copy()
    df_good.to_csv(os.path.join(base, 'RACHA_MAESTRO.csv'), index=False)
    print(f"Limpio: {len(df_good)} filas, ultimo: {df_good['sorteo'].max()}")

print("=== DONE ===")
