import pandas as pd
import requests
import numpy as np
import logging
import time
import json
from flask import Flask, jsonify, request

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL del servicio ms_loader (usar nombre del servicio Docker)
MS_LOADER_URL = "http://ms_loader:8000"

# Inicializar Flask app
app = Flask(__name__)

# Variable global para almacenar el DataFrame
# En un entorno de producción, esto requeriría un manejo de concurrencia si se modificara
# por múltiples hilos, pero para una versión 'secuencial' simple, es suficiente.
GLOBAL_DF = None
GLOBAL_LOADING = False

# Función para cargar datos desde ms_loader (síncrona)
def load_data_from_loader_sequential():
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

def initial_data_load():
    """Realiza la carga inicial de datos al inicio del servicio."""
    global GLOBAL_DF, GLOBAL_LOADING
    logger.info("⏳ Iniciando carga inicial de datos (secuencial)...")
    GLOBAL_LOADING = True
    GLOBAL_DF = load_data_from_loader_sequential()
    GLOBAL_LOADING = False
    if GLOBAL_DF is not None:
        logger.info("✅ Carga inicial de datos completada.")
    else:
        logger.error("❌ No se pudieron cargar los datos iniciales.")
        logger.info("💡 Puedes intentar recargar manualmente con /stats/reload.")


# --- Endpoints de la API Flask ---

@app.route("/", methods=["GET", "OPTIONS"])
@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    """Health check y información del servicio."""
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    # Verificar conectividad con ms_loader
    loader_status_info = {}
    try:
        response = requests.get(f"{MS_LOADER_URL}/health", timeout=5)
        if response.status_code == 200:
            loader_status_info['status'] = "ok"
            loader_status_info['details'] = response.json()
        else:
            loader_status_info['status'] = "error"
            loader_status_info['details'] = f"HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        loader_status_info['status'] = "starting"
        loader_status_info['details'] = "Connection refused - ms_loader may be starting"
    except Exception as e:
        loader_status_info['status'] = "error"
        loader_status_info['details'] = str(e)

    # Mensaje contextual
    if GLOBAL_DF is not None:
        message = "Servicio funcionando correctamente"
    elif GLOBAL_LOADING:
        message = "Cargando datos desde ms_loader..."
    else:
        message = "Usa /stats/reload para cargar datos si ms_loader ya está listo"
    
    response = jsonify({
        "service": "ms_stats (Sequential)",
        "status": "running",
        "port": 8002,
        "data_loaded": GLOBAL_DF is not None,
        "loading": GLOBAL_LOADING,
        "records": len(GLOBAL_DF) if GLOBAL_DF is not None else 0,
        "ms_loader_connection": loader_status_info['status'],
        "ms_loader_status": loader_status_info['details'],
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
    return _corsify_response(response)

@app.route("/stats", methods=["GET", "OPTIONS"])
@app.route("/stats/", methods=["GET", "OPTIONS"])
@app.route("/stats/basic", methods=["GET", "OPTIONS"])
def get_basic_stats():
    """Obtener estadísticas básicas."""
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    if GLOBAL_DF is None:
        if GLOBAL_LOADING:
            return _corsify_response(jsonify({
                "error": "Datos cargando",
                "message": "El servicio está cargando datos, intenta en unos segundos"
            }), 503)
        else:
            return _corsify_response(jsonify({
                "error": "Datos no disponibles",
                "message": "El servicio no pudo cargar datos",
                "hint": "Usa /stats/reload para reintentar la carga"
            }), 503)
    try:
        numeric_df = GLOBAL_DF.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            response = jsonify({
                "message": "No hay columnas numéricas disponibles",
                "total_records": len(GLOBAL_DF),
                "available_columns": list(GLOBAL_DF.columns)
            })
            return _corsify_response(response)
        
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
            "total_records": len(GLOBAL_DF),
            "numeric_columns": list(numeric_df.columns),
            "service": "ms_stats (Sequential)"
        }
        
        return _corsify_response(jsonify(result))
        
    except Exception as e:
        logger.error(f"Error calculando estadísticas básicas: {e}")
        return _corsify_response(jsonify({"error": f"Error calculando estadísticas: {str(e)}"}), 500)

@app.route("/stats/summary", methods=["GET", "OPTIONS"])
def get_summary():
    """Obtener resumen de datos."""
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    if GLOBAL_DF is None:
        if GLOBAL_LOADING:
            return _corsify_response(jsonify({
                "error": "Datos cargando",
                "message": "El servicio está cargando datos, intenta en unos segundos"
            }), 503)
        else:
            return _corsify_response(jsonify({
                "error": "Datos no disponibles",
                "message": "El servicio no pudo cargar datos",
                "hint": "Usa /stats/reload para reintentar la carga"
            }), 503)
    try:
        summary = {
            "service": "ms_stats (Sequential)",
            "total_records": len(GLOBAL_DF),
            "columns": list(GLOBAL_DF.columns),
            "data_types": GLOBAL_DF.dtypes.astype(str).to_dict(),
            "missing_values": GLOBAL_DF.isnull().sum().to_dict(),
            "memory_usage": f"{GLOBAL_DF.memory_usage().sum() / 1024 / 1024:.2f} MB"
        }
        
        if 'ticker' in GLOBAL_DF.columns:
            summary["unique_tickers"] = int(GLOBAL_DF['ticker'].nunique())
            summary["sample_tickers"] = sorted(GLOBAL_DF['ticker'].unique().tolist())[:10]
        
        if 'date' in GLOBAL_DF.columns:
            # Asegúrate de que 'date' sea de tipo datetime si es posible, para min/max correctos
            # O convertir a string si no se procesa como datetime en el cargador
            summary["date_range"] = {
                "start": str(GLOBAL_DF['date'].min()),
                "end": str(GLOBAL_DF['date'].max())
            }
        
        return _corsify_response(jsonify(summary))
        
    except Exception as e:
        logger.error(f"Error generando resumen: {e}")
        return _corsify_response(jsonify({"error": f"Error generando resumen: {str(e)}"}), 500)

@app.route("/stats/prices", methods=["GET", "OPTIONS"])
def get_price_stats():
    """Obtener estadísticas de precios."""
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    if GLOBAL_DF is None:
        if GLOBAL_LOADING:
            return _corsify_response(jsonify({
                "error": "Datos cargando",
                "message": "El servicio está cargando datos, intenta en unos segundos"
            }), 503)
        else:
            return _corsify_response(jsonify({
                "error": "Datos no disponibles",
                "message": "El servicio no pudo cargar datos",
                "hint": "Usa /stats/reload para reintentar la carga"
            }), 503)
    try:
        price_columns = ['open', 'high', 'low', 'close']
        available_price_cols = [col for col in price_columns if col in GLOBAL_DF.columns]
        
        if not available_price_cols:
            response = jsonify({
                "message": "No hay columnas de precios disponibles",
                "available_columns": list(GLOBAL_DF.columns),
                "service": "ms_stats (Sequential)"
            })
            return _corsify_response(response)
        
        price_data = GLOBAL_DF[available_price_cols]
        
        stats = {
            "service": "ms_stats (Sequential)",
            "price_statistics": {
                "mean": price_data.mean().to_dict(),
                "std": price_data.std().to_dict(),
                "min": price_data.min().to_dict(),
                "max": price_data.max().to_dict(),
                "median": price_data.median().to_dict()
            },
            "available_price_columns": available_price_cols,
            "total_records": len(GLOBAL_DF)
        }
        
        return _corsify_response(jsonify(stats))
        
    except Exception as e:
        logger.error(f"Error calculando estadísticas de precios: {e}")
        return _corsify_response(jsonify({"error": f"Error calculando estadísticas de precios: {str(e)}"}), 500)

@app.route("/stats/by_ticker/<ticker>", methods=["GET", "OPTIONS"])
def get_ticker_stats(ticker: str):
    """Obtener estadísticas para un ticker específico."""
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    if GLOBAL_DF is None:
        if GLOBAL_LOADING:
            return _corsify_response(jsonify({
                "error": "Datos cargando",
                "message": "El servicio está cargando datos, intenta en unos segundos"
            }), 503)
        else:
            return _corsify_response(jsonify({
                "error": "Datos no disponibles",
                "message": "El servicio no pudo cargar datos",
                "hint": "Usa /stats/reload para reintentar la carga"
            }), 503)

    try:
        if 'ticker' not in GLOBAL_DF.columns:
            return _corsify_response(jsonify({
                "error": "Columna 'ticker' no disponible en el dataset"
            }), 400)
        
        ticker_data = GLOBAL_DF[GLOBAL_DF['ticker'] == ticker.upper()]
        
        if ticker_data.empty:
            available_tickers = sorted(GLOBAL_DF['ticker'].unique().tolist())[:10]
            return _corsify_response(jsonify({
                "error": f"No se encontraron datos para {ticker}",
                "available_tickers_sample": available_tickers
            }), 404)
        
        numeric_data = ticker_data.select_dtypes(include=[np.number])
        
        stats = {
            "service": "ms_stats (Sequential)",
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
        
        return _corsify_response(jsonify(stats))
        
    except Exception as e:
        logger.error(f"Error calculando estadísticas para {ticker}: {e}")
        return _corsify_response(jsonify({"error": f"Error calculando estadísticas para {ticker}: {str(e)}"}), 500)

@app.route("/stats/reload", methods=["GET", "OPTIONS"])
def reload_data_endpoint():
    """Endpoint para recargar los datos manualmente."""
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    global GLOBAL_DF, GLOBAL_LOADING
    logger.info("🔄 Recibida petición de reload manual")
    
    if GLOBAL_LOADING:
        return _corsify_response(jsonify({
            "success": False,
            "message": "Ya hay una carga en progreso, por favor espera."
        }), 409) # 409 Conflict
    
    GLOBAL_LOADING = True
    try:
        new_df = load_data_from_loader_sequential()
        success = new_df is not None
        
        if success:
            GLOBAL_DF = new_df
            logger.info(f"✅ Datos recargados exitosamente: {len(GLOBAL_DF)} registros")
        else:
            logger.error("❌ Error recargando datos")
        
        response = jsonify({
            "success": success,
            "message": "Datos recargados exitosamente" if success else "Error recargando datos - verifica que ms_loader esté disponible",
            "records": len(GLOBAL_DF) if GLOBAL_DF is not None else 0,
            "columns": list(GLOBAL_DF.columns) if GLOBAL_DF is not None else [],
            "loading": GLOBAL_LOADING # Esto será falso justo después del finally
        })
        return _corsify_response(response)
    finally:
        GLOBAL_LOADING = False

# --- Funciones de soporte CORS ---
def _build_cors_preflight_response():
    response = jsonify({})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return response

def _corsify_response(response, status_code=200):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.status_code = status_code
    return response

# Punto de entrada principal para Flask
if __name__ == "__main__":
    # Realizar la carga inicial de datos antes de iniciar el servidor Flask
    initial_data_load()
    logger.info("🚀 Iniciando ms_stats (Versión Secuencial) en puerto 8002...")
    app.run(host="0.0.0.0", port=8002)