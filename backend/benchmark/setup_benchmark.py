#!/usr/bin/env python3
"""
Script de configuración para el entorno de benchmark
Instala dependencias y verifica la configuración
"""

import subprocess
import sys
import os
from pathlib import Path
import requests
import time

def install_dependencies():
    """Instala todas las dependencias necesarias"""
    print("📦 Instalando dependencias de Python...")
    
    dependencies = [
        'requests',
        'aiohttp',
        'matplotlib',
        'numpy',
        'pandas',
        'seaborn',
        'psutil',
        'flask',
        'ray[serve]'
    ]
    
    for dep in dependencies:
        try:
            print(f"   Instalando {dep}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error instalando {dep}: {e}")
            return False
    
    print("✅ Todas las dependencias instaladas correctamente")
    return True

def create_requirements_file():
    """Crea archivo requirements.txt"""
    requirements_content = """# Dependencias para el sistema de benchmark ms_stats
requests>=2.28.0
aiohttp>=3.8.0
matplotlib>=3.5.0
numpy>=1.21.0
pandas>=1.4.0
seaborn>=0.11.0
psutil>=5.8.0
flask>=2.0.0
ray[serve]>=2.0.0
"""
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements_content)
    
    print("✅ Archivo requirements.txt creado")

def check_python_version():
    """Verifica la versión de Python"""
    print("🐍 Verificando versión de Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} no es compatible")
        print("💡 Se requiere Python 3.8 o superior")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def create_directory_structure():
    """Crea la estructura de directorios necesaria"""
    print("📁 Creando estructura de directorios...")
    
    directories = [
        'benchmark_plots',
        'benchmark_results',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ {directory}/")
    
    print("✅ Estructura de directorios creada")

def create_docker_compose_example():
    """Crea un ejemplo de docker-compose para los servicios"""
    docker_compose_content = """version: '3.8'

services:
  ms_loader:
    build: ./ms_loader
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./data:/app/data
    networks:
      - ms_network

  ms_stats_ray:
    build: 
      context: ./ms_stats
      dockerfile: Dockerfile.ray
    ports:
      - "8001:8001"
    depends_on:
      - ms_loader
    environment:
      - PYTHONUNBUFFERED=1
      - MS_LOADER_URL=http://ms_loader:8000
    networks:
      - ms_network

  ms_stats_flask:
    build:
      context: ./ms_stats
      dockerfile: Dockerfile.flask
    ports:
      - "8002:8002"
    depends_on:
      - ms_loader
    environment:
      - PYTHONUNBUFFERED=1
      - MS_LOADER_URL=http://ms_loader:8000
    networks:
      - ms_network

networks:
  ms_network:
    driver: bridge

volumes:
  data_volume:
"""
    
    with open('docker-compose.benchmark.yml', 'w') as f:
        f.write(docker_compose_content)
    
    print("✅ Archivo docker-compose.benchmark.yml creado")

def create_benchmark_config():
    """Crea archivo de configuración para el benchmark"""
    config_content = """# Configuración del Benchmark - ms_stats

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
"""
    
    with open('benchmark_config.py', 'w') as f:
        f.write(config_content)
    
    print("✅ Archivo benchmark_config.py creado")

def wait_for_services():
    """Espera a que los servicios estén disponibles"""
    print("⏳ Esperando a que los servicios estén disponibles...")
    
    services = [
        ("ms_loader", "http://localhost:8000/health"),
        ("ms_stats_ray", "http://localhost:8001/health"), 
        ("ms_stats_flask", "http://localhost:8002/health")
    ]
    
    max_wait = 300  # 5 minutos
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        all_ready = True
        
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if name == "ms_loader":
                        # Para ms_loader, verificar que tenga datos
                        if not data.get('data_loaded', False):
                            all_ready = False
                            break
                    else:
                        # Para ms_stats, verificar que pueda conectar con ms_loader
                        if data.get('records', 0) == 0:
                            all_ready = False
                            break
                    print(f"   ✅ {name}: OK")
                else:
                    all_ready = False
                    print(f"   ⏳ {name}: Iniciando...")
                    break
            except Exception:
                all_ready = False
                print(f"   ⏳ {name}: Esperando...")
                break
        
        if all_ready:
            print("✅ Todos los servicios están listos")
            return True
        
        time.sleep(10)
    
    print("❌ Timeout esperando servicios")
    return False

def run_quick_test():
    """Ejecuta una prueba rápida del sistema"""
    print("🧪 Ejecutando prueba rápida del sistema...")
    
    try:
        # Importar y ejecutar un benchmark muy básico
        import asyncio
        import aiohttp
        
        async def quick_test():
            services = [
                ("Ray Serve", "http://localhost:8001/health"),
                ("Flask", "http://localhost:8002/health")
            ]
            
            async with aiohttp.ClientSession() as session:
                for name, url in services:
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                print(f"   ✅ {name}: Responde correctamente")
                            else:
                                print(f"   ❌ {name}: Error {response.status}")
                    except Exception as e:
                        print(f"   ❌ {name}: {e}")
        
        asyncio.run(quick_test())
        print("✅ Prueba rápida completada")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba rápida: {e}")
        return False

def show_next_steps():
    """Muestra los siguientes pasos al usuario"""
    print("\n" + "="*60)
    print("🎉 CONFIGURACIÓN COMPLETADA")
    print("="*60)
    print("\n📋 Siguientes pasos:")
    print("1. Asegúrate de que tus servicios estén corriendo:")
    print("   • ms_loader en puerto 8000")
    print("   • ms_stats (Ray) en puerto 8001") 
    print("   • ms_stats (Flask) en puerto 8002")
    print("\n2. Si usas Docker, ejecuta:")
    print("   docker-compose -f docker-compose.benchmark.yml up -d")
    print("\n3. Ejecuta el benchmark:")
    print("   python run_benchmark.py")
    print("\n4. O ejecuta una prueba rápida:")
    print("   python run_benchmark.py --quick")
    print("\n📁 Archivos creados:")
    print("   • requirements.txt - Dependencias")
    print("   • benchmark_config.py - Configuración")
    print("   • docker-compose.benchmark.yml - Docker compose")
    print("   • benchmark_plots/ - Directorio para gráficos")
    print("="*60)

def main():
    """Función principal de configuración"""
    print("🚀 Configuración del Sistema de Benchmark - ms_stats")
    print("="*60)
    
    # Verificar Python
    if not check_python_version():
        return False
    
    # Crear estructura
    create_directory_structure()
    
    # Crear archivos de configuración
    create_requirements_file()
    create_docker_compose_example()
    create_benchmark_config()
    
    # Instalar dependencias
    install_dependencies()
    
    # Mostrar siguientes pasos
    show_next_steps()
    
    return True

def main_with_services():
    """Configuración completa incluyendo espera de servicios"""
    print("🚀 Configuración Completa del Sistema de Benchmark")
    print("="*60)
    
    # Configuración básica
    if not main():
        return False
    
    # Esperar servicios
    print("\n⏳ Esperando servicios...")
    if wait_for_services():
        # Ejecutar prueba rápida
        run_quick_test()
        
        print("\n🎉 Sistema completamente configurado y probado!")
        print("💡 Ejecuta: python run_benchmark.py")
    else:
        print("\n⚠️ Servicios no disponibles, pero configuración completada")
        print("💡 Inicia tus servicios y luego ejecuta el benchmark")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--wait-services":
        # Configuración completa con espera de servicios
        success = main_with_services()
    else:
        # Solo configuración básica
        success = main()
    
    if not success:
        sys.exit(1)