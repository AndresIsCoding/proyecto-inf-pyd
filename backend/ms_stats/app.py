import pandas as pd
import ray
from ray import serve
import requests
import numpy as np
from typing import Dict, Any
import logging
import os
from starlette.requests import Request
from starlette.responses import JSONResponse
import asyncio
import json
import time
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL del servicio ms_loader (usar nombre del servicio Docker)
MS_LOADER_URL = "http://ms_loader:8000"

# Función para cargar datos desde ms_loader
def load_data_from_loader():
    """Carga datos desde el microservicio ms_loader usando la red Docker."""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Intento {attempt + 1}/{max_retries}: Cargando datos desde {MS_LOADER_URL}")
            
            # Verificar que el servicio esté disponible
            health_response = requests.get(f"{MS_LOADER_URL}/health", timeout=10)
            if health_response.status_code != 200:
                raise Exception(f"ms_loader no está disponible. Status: {health_response.status_code}")
            
            health_data = health_response.json()
            logger.info(f"ms_loader status: {health_data}")
            
            # Verificar si ms_loader está cargando datos
            if 'loading' in health_data and health_data['loading']:
                logger.info("ms_loader está cargando datos, esperando...")
                raise Exception("ms_loader está cargando datos")
            
            # Verificar si ms_loader tiene datos
            if not health_data.get('data_loaded', False) or health_data.get('records', 0) == 0:
                logger.info("ms_loader no tiene datos cargados aún, esperando...")
                raise Exception("ms_loader no tiene datos cargados")
            
            # Obtener los datos
            logger.info("Descargando dataset...")
            response = requests.get(f"{MS_LOADER_URL}/dataset", timeout=120)
            if response.status_code != 200:
                raise Exception(f"Error al obtener datos: {response.status_code}")
            
            # Convertir JSON a DataFrame
            data = response.json()
            if not data:
                raise Exception("Dataset vacío recibido de ms_loader")
            
            df = pd.DataFrame(data)
            
            # Limpiar datos
            df = df.dropna()
            
            logger.info(f"✅ Datos cargados exitosamente: {len(df)} registros")
            logger.info(f"Columnas disponibles: {list(df.columns)}")
            
            return df
            
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Intento {attempt + 1} falló - Error de conexión: {e}")
        except requests.exceptions.Timeout as e:
            logger.warning(f"Intento {attempt + 1} falló - Timeout: {e}")
        except Exception as e:
            logger.warning(f"Intento {attempt + 1} falló - Error: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"Esperando {retry_delay} segundos antes del siguiente intento...")
            time.sleep(retry_delay)
    
    logger.error(f"❌ No se pudieron cargar los datos después de {max_retries} intentos")
    return None

# Deployment unificado para manejar todas las rutas
@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 1}
)
class StatsApp:
    def __init__(self):
        logger.info("Inicializando StatsApp...")
        self.df = None
        self.loading = False
        self._load_data_initial()
    
    def _load_data_initial(self):
        """Carga inicial de datos - intenta cargar inmediatamente y luego en background."""
        logger.info("⏳ Iniciando carga inicial de datos...")
        
        # Primero intentar cargar inmediatamente (para casos donde ms_loader ya está listo)
        try:
            logger.info("🔄 Intentando carga inmediata...")
            self.df = load_data_from_loader()
            if self.df is not None:
                logger.info("✅ Datos cargados inmediatamente")
                return
        except Exception as e:
            logger.info(f"Carga inmediata falló: {e}")
        
        # Si la carga inmediata falló, iniciar background loading
        logger.info("📋 Iniciando carga en segundo plano...")
        self.loading = True
        
        def background_load():
            try:
                # Esperar un poco más para que ms_loader termine de cargar
                time.sleep(10)
                logger.info("🔄 Intentando cargar datos desde ms_loader en background...")
                
                df = load_data_from_loader()
                if df is not None:
                    self.df = df
                    logger.info("✅ Datos cargados correctamente en background")
                else:
                    logger.warning("⚠️ No se pudieron cargar datos en background")
                    logger.info("💡 Usa 'curl http://localhost:8001/stats/reload' para reintentar")
            except Exception as e:
                logger.error(f"Error en background loading: {e}")
            finally:
                self.loading = False
        
        # Iniciar carga en background
        thread = threading.Thread(target=background_load, daemon=True)
        thread.start()
        
        logger.info("✅ StatsApp inicializado - cargando datos...")
    
    def reload_data(self):
        """Recarga los datos desde ms_loader."""
        logger.info("🔄 Recargando datos manualmente...")
        
        if self.loading:
            logger.info("⏳ Ya hay una carga en progreso...")
            return False
        
        self.loading = True
        try:
            self.df = load_data_from_loader()
            success = self.df is not None
            
            if success:
                logger.info(f"✅ Datos recargados exitosamente: {len(self.df)} registros")
            else:
                logger.error("❌ Error recargando datos")
            
            return success
        finally:
            self.loading = False
    
    async def __call__(self, request: Request):
        path = request.url.path
        logger.info(f"Procesando request: {path}")
        
        try:
            # Ruta principal y health check
            if path == "/" or path == "/health":
                return await self._get_health()
            
            # Verificar si hay datos disponibles para rutas de stats
            if path.startswith("/stats") and path != "/stats/reload":
                if self.df is None:
                    if self.loading:
                        return JSONResponse(
                            status_code=503,
                            content={
                                "error": "Datos cargando",
                                "message": "El servicio está cargando datos desde ms_loader, intenta en unos segundos"
                            }
                        )
                    else:
                        return JSONResponse(
                            status_code=503,
                            content={
                                "error": "Datos no disponibles",
                                "message": "El servicio no pudo cargar datos desde ms_loader",
                                "hint": "Usa /stats/reload para reintentar la carga"
                            }
                        )
            
            # Rutas de estadísticas
            if path == "/stats" or path == "/stats/" or path == "/stats/basic":
                return await self._get_basic_stats()
            elif path == "/stats/summary":
                return await self._get_summary()
            elif path == "/stats/prices":
                return await self._get_price_stats()
            elif path.startswith("/stats/by_ticker/"):
                ticker = path.split("/stats/by_ticker/")[-1]
                return await self._get_ticker_stats(ticker)
            elif path == "/stats/reload":
                logger.info("🔄 Recibida petición de reload manual")
                success = self.reload_data()
                return JSONResponse(content={
                    "success": success,
                    "message": "Datos recargados exitosamente" if success else "Error recargando datos - verifica que ms_loader esté disponible",
                    "records": len(self.df) if self.df is not None else 0,
                    "columns": list(self.df.columns) if self.df is not None else [],
                    "loading": self.loading
                })
            else:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "Endpoint no encontrado",
                        "available_endpoints": [
                            "/",
                            "/health",
                            "/stats/",
                            "/stats/basic", 
                            "/stats/summary",
                            "/stats/prices",
                            "/stats/by_ticker/{ticker}",
                            "/stats/reload"
                        ]
                    }
                )
                
        except Exception as e:
            logger.error(f"Error en StatsApp: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error interno: {str(e)}"}
            )
    
    async def _get_health(self):
        """Health check y información del servicio."""
        try:
            # Verificar conectividad con ms_loader
            try:
                response = requests.get(f"{MS_LOADER_URL}/health", timeout=5)
                if response.status_code == 200:
                    loader_status = response.json()
                    loader_connection = "ok"
                else:
                    loader_status = f"HTTP {response.status_code}"
                    loader_connection = "error"
            except requests.exceptions.ConnectionError:
                loader_status = "Connection refused - ms_loader may be starting"
                loader_connection = "starting"
            except Exception as e:
                loader_status = str(e)
                loader_connection = "error"
            
            # Mensaje contextual
            if self.df is not None:
                message = "Servicio funcionando correctamente"
            elif self.loading:
                message = "Cargando datos desde ms_loader..."
            else:
                message = "Usa /stats/reload para cargar datos si ms_loader ya está listo"
            
            return JSONResponse(content={
                "service": "ms_stats with Ray Serve",
                "status": "running",
                "port": 8001,
                "data_loaded": self.df is not None,
                "loading": self.loading,
                "records": len(self.df) if self.df is not None else 0,
                "ms_loader_connection": loader_connection,
                "ms_loader_status": loader_status,
                "message": message,
                "endpoints": {
                    "health": "/health",
                    "basic_stats": "/stats/basic",
                    "summary": "/stats/summary", 
                    "prices": "/stats/prices",
                    "by_ticker": "/stats/by_ticker/{ticker}",
                    "reload": "/stats/reload"
                }
            })
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Error verificando estado: {str(e)}"}
            )
    
    async def _get_basic_stats(self):
        """Obtener estadísticas básicas."""
        try:
            numeric_df = self.df.select_dtypes(include=[np.number])
            
            if numeric_df.empty:
                return JSONResponse(content={
                    "message": "No hay columnas numéricas disponibles",
                    "total_records": len(self.df),
                    "available_columns": list(self.df.columns)
                })
            
            stats = {
                "mean": numeric_df.mean().to_dict(),
                "std": numeric_df.std().to_dict(),
                "min": numeric_df.min().to_dict(),
                "max": numeric_df.max().to_dict(),
                "median": numeric_df.median().to_dict(),
                "count": numeric_df.count().to_dict()
            }
            
            result = {
                "statistics": stats,
                "total_records": len(self.df),
                "numeric_columns": list(numeric_df.columns),
                "service": "ms_stats with Ray Serve"
            }
            
            return JSONResponse(content=result)
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas básicas: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error calculando estadísticas: {str(e)}"}
            )
    
    async def _get_summary(self):
        """Obtener resumen de datos."""
        try:
            summary = {
                "service": "ms_stats with Ray Serve",
                "total_records": len(self.df),
                "columns": list(self.df.columns),
                "data_types": self.df.dtypes.astype(str).to_dict(),
                "missing_values": self.df.isnull().sum().to_dict(),
                "memory_usage": f"{self.df.memory_usage().sum() / 1024 / 1024:.2f} MB"
            }
            
            if 'ticker' in self.df.columns:
                summary["unique_tickers"] = int(self.df['ticker'].nunique())
                summary["sample_tickers"] = sorted(self.df['ticker'].unique().tolist())[:10]
            
            if 'date' in self.df.columns:
                summary["date_range"] = {
                    "start": str(self.df['date'].min()),
                    "end": str(self.df['date'].max())
                }
            
            return JSONResponse(content=summary)
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error generando resumen: {str(e)}"}
            )
    
    async def _get_price_stats(self):
        """Obtener estadísticas de precios."""
        try:
            price_columns = ['open', 'high', 'low', 'close']
            available_price_cols = [col for col in price_columns if col in self.df.columns]
            
            if not available_price_cols:
                return JSONResponse(content={
                    "message": "No hay columnas de precios disponibles",
                    "available_columns": list(self.df.columns),
                    "service": "ms_stats with Ray Serve"
                })
            
            price_data = self.df[available_price_cols]
            
            stats = {
                "service": "ms_stats with Ray Serve",
                "price_statistics": {
                    "mean": price_data.mean().to_dict(),
                    "std": price_data.std().to_dict(),
                    "min": price_data.min().to_dict(),
                    "max": price_data.max().to_dict(),
                    "median": price_data.median().to_dict()
                },
                "available_price_columns": available_price_cols,
                "total_records": len(self.df)
            }
            
            return JSONResponse(content=stats)
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas de precios: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error calculando estadísticas de precios: {str(e)}"}
            )
    
    async def _get_ticker_stats(self, ticker: str):
        """Obtener estadísticas para un ticker específico."""
        try:
            if 'ticker' not in self.df.columns:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Columna 'ticker' no disponible en el dataset"}
                )
            
            ticker_data = self.df[self.df['ticker'] == ticker.upper()]
            
            if ticker_data.empty:
                available_tickers = sorted(self.df['ticker'].unique().tolist())[:10]
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": f"No se encontraron datos para {ticker}",
                        "available_tickers_sample": available_tickers
                    }
                )
            
            numeric_data = ticker_data.select_dtypes(include=[np.number])
            
            stats = {
                "service": "ms_stats with Ray Serve",
                "ticker": ticker.upper(),
                "records": len(ticker_data),
                "statistics": {
                    "mean": numeric_data.mean().to_dict(),
                    "std": numeric_data.std().to_dict(),
                    "min": numeric_data.min().to_dict(),
                    "max": numeric_data.max().to_dict(),
                    "median": numeric_data.median().to_dict()
                },
                "numeric_columns": list(numeric_data.columns)
            }
            
            return JSONResponse(content=stats)
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas para {ticker}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error calculando estadísticas para {ticker}: {str(e)}"}
            )

# Función principal para inicializar todo
def main():
    """Inicializa Ray y despliega el servicio."""
    logger.info("🚀 Iniciando ms_stats con Ray Serve...")

    try:
        # Inicializar Ray (solo si no está ya inicializado)
        if not ray.is_initialized():
            ray.init(
                ignore_reinit_error=True,
                include_dashboard=False,
                log_to_driver=True
            )
            logger.info("Ray inicializado correctamente")
        else:
            logger.info("Ray ya estaba inicializado")

        # Inicializar Serve con configuración simple
        serve.start(
            detached=True,
            http_options={
                "host": "0.0.0.0",
                "port": 8001
            }
        )
        logger.info("Ray Serve iniciado en puerto 8001")
        
        # Crear y desplegar la aplicación
        app = StatsApp.bind()
        serve.run(app, name="stats_app")

        logger.info("✅ Servicio desplegado correctamente")
        logger.info("📊 Endpoints disponibles:")
        logger.info("   • http://0.0.0.0:8001/ - Estado del servicio")
        logger.info("   • http://0.0.0.0:8001/health - Health check")
        logger.info("   • http://0.0.0.0:8001/stats/ - Estadísticas básicas")
        logger.info("   • http://0.0.0.0:8001/stats/basic - Estadísticas básicas")
        logger.info("   • http://0.0.0.0:8001/stats/summary - Resumen de datos")
        logger.info("   • http://0.0.0.0:8001/stats/prices - Estadísticas de precios")
        logger.info("   • http://0.0.0.0:8001/stats/by_ticker/AAPL - Stats por ticker")
        logger.info("   • http://0.0.0.0:8001/stats/reload - Recargar datos")

        return True

    except Exception as e:
        logger.error(f"❌ Error iniciando servicio: {e}")
        return False

# Función para mantener el servicio corriendo
def keep_alive():
    """Mantiene el servicio corriendo y verifica su estado."""
    try:
        logger.info("✅ Servicio iniciado. Presiona Ctrl+C para detener...")
        while True:
            time.sleep(60)  # Verificar cada minuto
            try:
                status = serve.status()
                logger.info("✅ Servicio funcionando correctamente")
            except Exception as e:
                logger.warning(f"⚠️ Error verificando estado: {e}")
                
    except KeyboardInterrupt:
        logger.info("🛑 Deteniendo servicios...")
        try:
            serve.shutdown()
            ray.shutdown()
            logger.info("✅ Servicios detenidos correctamente")
        except Exception as e:
            logger.error(f"Error deteniendo servicios: {e}")

# Punto de entrada principal
if __name__ == "__main__":
    if main():
        keep_alive()
    else:
        logger.error("❌ No se pudo iniciar el servicio")
        exit(1)
else:
    # Cuando se importa (para Docker), inicializar automáticamente
    logger.info("Módulo importado, iniciando servicios...")
    main()