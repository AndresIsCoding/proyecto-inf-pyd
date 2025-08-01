# Configuración del Benchmark - ms_stats

## URLs de los servicios
RAY_SERVE_URL = "http://localhost:8001"
FLASK_URL = "http://localhost:8002"

## Configuración de pruebas
WARMUP_REQUESTS = 10
TEST_DURATIONS = [30, 60]  # segundos
CONCURRENT_USERS = [1, 5, 10, 20, 50]

## Endpoints a probar
ENDPOINTS = [
    "/health",
    "/stats/basic", 
    "/stats/summary",
    "/stats/prices",
    "/stats/by_ticker/AAPL"
]

## Configuración de sistema
MONITOR_INTERVAL = 0.5  # segundos
MAX_RETRIES = 5
TIMEOUT = 30  # segundos

## Configuración de gráficos
FIGURE_SIZE = (12, 8)
DPI = 300
PLOT_STYLE = 'seaborn-v0_8'
