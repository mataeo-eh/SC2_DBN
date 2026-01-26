import pandas as pd
from pathlib import Path

data_dir = Path("data/quickstart")

for file in data_dir.glob("*.parquet"):
    print(f"Loading {file}...")
    df = pd.read_parquet(file)
    pd.set_option('display.max_columns', None) 
    print(df.head())
    print()