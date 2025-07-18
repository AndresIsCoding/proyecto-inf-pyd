from fastapi import FastAPI
import pandas as pd

app = FastAPI()

# Carga del dataset
df = pd.read_csv('backend\ms_loader\HousingData.csv')

# Eliminación de las filas con valores NaN
df = df.dropna()

# Eliminacion de las variables que no se van a utilizar
df = df.drop(columns=['B', 'CHAS', 'ZN', 'INDUS', 'RAD'])

# Seleccion de variables para el entrenamiento
features = ["RM","LSTAT", "PTRATIO", "DIS", "TAX"]
target = "MEDV"

x = df[features]
y = df[target]

# Dataset ya procesado y exportado
df_final = df[features + [target]]

@app.get("/dataset")
def get_processed_dataset():
    return df_final.to_dict(orient="records")


print(df_final.head())