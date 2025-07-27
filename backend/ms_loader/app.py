from fastapi import FastAPI
from fastapi.responses import JSONResponse
import pandas as pd
<<<<<<< Updated upstream

app = FastAPI()

# Cargar el listado de empresas
sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
sp500 = sp500.dropna()
sp500['Symbol'] = sp500['Symbol'].str.replace('.','-')
symbol_list = sp500['Symbol'].unique().tolist()

# Fechas 
end_date = '2023-09-27'
start_date = pd.to_datetime(end_date)-pd.DateOffset(365*8)

# Construccion del dataset

df = yf.download(tickers=symbol_list,start=start_date,end=end_date).stack()
df.index.names = ['date','ticker']
df.columns = df.columns.str.lower()

# Dataset listo para ser pasado a ms_stats
@app.get("/dataset")
def get_processed_dataset():
    return df.reset_index().to_dict(orient="records")


print(df_final.head())
=======
import yfinance as yf
import numpy as np
import warnings

app = FastAPI()

@app.get("/")
def root():
    return {"message": "ms_loader activo"}

warnings.simplefilter(action='ignore', category=FutureWarning)

sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
sp500 = sp500.dropna()
sp500['Symbol'] = sp500['Symbol'].str.replace('.', '-', regex=False)
symbol_list = sp500['Symbol'].unique().tolist()
symbol_list = [s for s in symbol_list if s not in ['GEV', 'VLTO', 'SOLV']]

start_date = "2024-01-01"
end_date = "2024-12-31"

all_data = []
chunk_size = 20

for i in range(0, len(symbol_list), chunk_size):
    chunk = symbol_list[i:i + chunk_size]
    try:
        df_chunk = yf.download(
            tickers=chunk,
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=False
        )
        df_chunk = df_chunk.stack(future_stack=True)
        df_chunk.index.names = ['date', 'ticker']
        df_chunk.columns = df_chunk.columns.str.lower()
        all_data.append(df_chunk)
    except Exception as e:
        print(f"Error descargando chunk {chunk}: {e}")

df = pd.concat(all_data)
df = df.reset_index()
df.dropna(inplace=True)
df['date'] = df['date'].astype(str)

@app.get("/dataset")
def get_dataset():
    return JSONResponse(content=df.to_dict(orient="records"))
>>>>>>> Stashed changes
