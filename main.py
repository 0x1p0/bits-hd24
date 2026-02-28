import pandas as pd
import json

# Load
df = pd.read_csv("BITS HD Admissions - Responses - 2024.csv")

# Drop completely empty rows
df = df.dropna(how="all")

# Clean column names (remove extra spaces)
df.columns = df.columns.str.strip()

# Optional: fill NaN with None (better JSON)
df = df.where(pd.notnull(df), None)

# Convert to JSON
df.to_json("bits_hd_2024.json", orient="records", indent=4)

print("JSON file created: bits_hd_2024.json")