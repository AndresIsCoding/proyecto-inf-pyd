from fastapi import FastAPI
import pandas as pd
import ray
from ray import serve
from typing import Dict, Any
import numpy as np  # Corrección: usar np.nan en vez de importar NaN

# Inicializar Ray y Ray Serve
ray.init(ignore_reinit_error=True)
serve.start(detached=True)

# Cargar dataset desde el microservicio ms_loader
df = pd.read_csv("http://localhost:8000/dataset")  # Asume que ms_loader está corriendo

# Eliminar NaN por seguridad adicional
df = df.dropna()

# Microservicio de estadísticas
@serve.deployment(route_prefix="/stats", ray_actor_options={"num_cpus": 1})
class StatsService:
    def __init__(self):
        self.df = df.copy()

    async def __call__(self, request):
        stats = {
            "mean": self.df.mean(numeric_only=True).to_dict(),
            "std": self.df.std(numeric_only=True).to_dict(),
            "min": self.df.min(numeric_only=True).to_dict(),
            "max": self.df.max(numeric_only=True).to_dict()
        }
        return stats

# Deploy del servicio
StatsService.deploy()

# Inicializar FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"message": "ms_stats activo"}

@app.get("/stats/")
def procesar() -> Dict[str, Any]:
    handle = StatsService.get_handle()
    result = ray.get(handle.remote(None))
    return result
