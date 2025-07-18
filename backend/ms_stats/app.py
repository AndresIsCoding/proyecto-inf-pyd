import ray
import requests
import pandas as pd
from fastapi import FastAPI

ray.init(ignore_reinit_error=True)

app = FastAPI()

@ray.remote
def calcular_media(df_dict):
    df = pd.DataFrame(df_dict)
    return df.mean().to_dict()
