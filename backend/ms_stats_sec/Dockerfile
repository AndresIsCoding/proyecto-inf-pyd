# Dockerfile para ms_stats
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt  

RUN pip install async_timeout pandas


# Copiar código fuente
COPY . .

# Exponer puerto
EXPOSE 8001

# Variables de entorno para Ray
ENV RAY_DISABLE_IMPORT_WARNING=1
ENV RAY_USAGE_STATS_ENABLED=0
ENV RAY_DEDUP_LOGS=0
ENV RAY_DISABLE_IMPORT_WARNING=1
ENV RAY_HEAD_NODE_HOST=127.0.0.1
ENV PYTHONUNBUFFERED=1

# Comando por defecto (será sobrescrito por docker-compose)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "python", "-u", "app.py"]