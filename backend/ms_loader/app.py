from fastapi import FastAPI
import pandas as pd
import yfinance as yf
import os

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

print(df.head())