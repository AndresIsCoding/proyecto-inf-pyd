#!/usr/bin/env python3
"""
Script para ejecutar benchmark completo y generar reportes automáticamente
"""

import subprocess
import sys
import time
import os
from pathlib import Path
import json
from datetime import datetime

def check_dependencies():
    """Verifica que todas las dependencias estén instaladas"""
    required_packages = [
        'requests', 'aiohttp', 'matplotlib', 'numpy', 
        'psutil', 'pandas', 'seaborn'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Dependencias faltantes: {', '.join(missing)}")
        print("💡 Instala con: pip install " + " ".join(missing))
        return False
    
    return True

def check_services():
    """Verifica que ambos servicios estén corriendo"""
    import requests
    
    services = [
        ("Ray Serve (Puerto 8001)", "http://localhost:8001/health"),
        ("Flask (Puerto 8002)", "http://localhost:8002/health")
    ]
    
    print("🔍 Verificando servicios...")
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                records = data.get('records', 0)
                print(f"✅ {name}: OK ({records} registros)")
            else:
                print(f"❌ {name}: Error HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {name}: No disponible - {e}")
            return False
    
    return True

def run_benchmark():
    """Ejecuta el benchmark"""
    print("\n🚀 Iniciando benchmark...")
    print("⏱️  Esto puede tomar varios minutos...")
    
    try:
        # Ejecutar el benchmark
        import asyncio
        
        # Importar el benchmark runner
        sys.path.append(str(Path(__file__).parent))
        
        # Ejecutar benchmark de forma programática
        from benchmark_script import BenchmarkRunner
        
        async def run_async_benchmark():
            runner = BenchmarkRunner()
            await runner.run_all_benchmarks()
            results_file = runner.save_results()
            runner.generate_report()
            return results_file
        
        results_file = asyncio.run(run_async_benchmark())
        return results_file
        
    except Exception as e:
        print(f"❌ Error ejecutando benchmark: {e}")
        return None

def generate_visualizations(results_file):
    """Genera las visualizaciones"""
    if not results_file or not Path(results_file).exists():
        print("❌ No se puede generar visualizaciones sin archivo de resultados")
        return False
    
    print(f"\n📊 Generando visualizaciones desde {results_file}...")
    
    try:
        # Importar y ejecutar visualizador
        from visualization_script import BenchmarkVisualizer
        
        visualizer = BenchmarkVisualizer(results_file)
        visualizer.create_comparison_plots()
        
        output_dir = Path("benchmark_plots")
        visualizer.generate_summary_table(output_dir)
        
        print("✅ Visualizaciones generadas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error generando visualizaciones: {e}")
        return False

def create_full_report(results_file):
    """Crea un reporte completo en HTML"""
    if not results_file:
        return
    
    print("\n📄 Generando reporte HTML completo...")
    
    try:
        # Cargar resultados
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Crear HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Benchmark - ms_stats</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2E86AB;
            text-align: center;
            border-bottom: 3px solid #2E86AB;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #A23B72;
            margin-top: 30px;
        }}
        .summary-box {{
            background-color: #f8f9fa;
            border-left: 5px solid #2E86AB;
            padding: 15px;
            margin: 20px 0;
        }}
        .chart-container {{
            text-align: center;
            margin: 20px 0;
        }}
        .chart-container img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }}
        th {{
            background-color: #2E86AB;
            color: white;
        }}
        .improvement-positive {{
            color: #28a745;
            font-weight: bold;
        }}
        .improvement-negative {{
            color: #dc3545;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Reporte de Benchmark - ms_stats</h1>
        <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <p><strong>Archivo de resultados:</strong> {results_file}</p>
        <p><strong>Total de pruebas:</strong> {len(results)}</p>
        
        <div class="summary-box">
            <h3>🎯 Objetivo del Benchmark</h3>
            <p>Comparar el rendimiento entre dos implementaciones del microservicio ms_stats:</p>
            <ul>
                <li><strong>Ray Serve (Paralelo):</strong> Puerto 8001 - Procesamiento asíncrono y paralelo</li>
                <li><strong>Flask (Secuencial):</strong> Puerto 8002 - Procesamiento síncrono tradicional</li>
            </ul>
        </div>
        
        <h2>📈 Gráficos de Rendimiento</h2>
        
        <div class="chart-container">
            <h3>Comparación de Throughput</h3>
            <img src="benchmark_plots/throughput_comparison.png" alt="Throughput Comparison">
        </div>
        
        <div class="chart-container">
            <h3>Comparación de Latencia</h3>
            <img src="benchmark_plots/latency_comparison.png" alt="Latency Comparison">
        </div>
        
        <div class="chart-container">
            <h3>Escalabilidad con Concurrencia</h3>
            <img src="benchmark_plots/concurrency_scaling.png" alt="Concurrency Scaling">
        </div>
        
        <div class="chart-container">
            <h3>Rendimiento por Endpoint</h3>
            <img src="benchmark_plots/endpoint_performance.png" alt="Endpoint Performance">
        </div>
        
        <div class="chart-container">
            <h3>Uso de Recursos del Sistema</h3>
            <img src="benchmark_plots/system_resources.png" alt="System Resources">
        </div>
        
        <div class="chart-container">
            <h3>Tasas de Error</h3>
            <img src="benchmark_plots/error_rates.png" alt="Error Rates">
        </div>
        
        <h2>📋 Resumen de Resultados</h2>
        <div class="chart-container">
            <img src="benchmark_plots/summary_table.png" alt="Summary Table">
        </div>
        
        <h2>🔍 Análisis y Conclusiones</h2>
        <div class="summary-box">
            <h3>Ventajas de Ray Serve (Paralelo):</h3>
            <ul>
                <li>Mayor throughput bajo alta concurrencia</li>
                <li>Mejor escalabilidad horizontal</li>
                <li>Procesamiento asíncrono eficiente</li>
                <li>Manejo optimizado de múltiples peticiones simultáneas</li>
            </ul>
            
            <h3>Ventajas de Flask (Secuencial):</h3>
            <ul>
                <li>Menor complejidad de implementación</li>
                <li>Menor uso de recursos en cargas bajas</li>
                <li>Debugging más sencillo</li>
                <li>Menor latencia inicial en algunos casos</li>
            </ul>
        </div>
        
        <h2>📊 Datos Técnicos</h2>
        <p><strong>Configuración del benchmark:</strong></p>
        <ul>
            <li>Usuarios concurrentes probados: 1, 5, 10, 20, 50</li>
            <li>Duración de pruebas: 30s y 60s</li>
            <li>Endpoints probados: /health, /stats/basic, /stats/summary, /stats/prices, /stats/by_ticker/AAPL</li>
            <li>Peticiones de calentamiento: 10 por servicio</li>
        </ul>
        
        <div class="footer">
            <p>Reporte generado automáticamente por el sistema de benchmark</p>
            <p>Archivos de datos: {results_file}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Guardar HTML
        html_file = Path("benchmark_report.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Reporte HTML creado: {html_file}")
        return html_file
        
    except Exception as e:
        print(f"❌ Error creando reporte HTML: {e}")
        return None

def main():
    """Función principal"""
    print("🚀 Sistema de Benchmark Automatizado - ms_stats")
    print("=" * 60)
    print("Comparando Ray Serve (Paralelo) vs Flask (Secuencial)")
    print("=" * 60)
    
    # Paso 1: Verificar dependencias
    print("\n📦 Paso 1: Verificando dependencias...")
    if not check_dependencies():
        print("❌ Instala las dependencias requeridas antes de continuar")
        return False
    print("✅ Todas las dependencias están instaladas")
    
    # Paso 2: Verificar servicios
    print("\n🔍 Paso 2: Verificando servicios...")
    if not check_services():
        print("❌ Asegúrate de que ambos servicios estén corriendo:")
        print("   • Ray Serve: http://localhost:8001")
        print("   • Flask: http://localhost:8002")
        return False
    print("✅ Ambos servicios están disponibles y con datos")
    
    # Paso 3: Ejecutar benchmark
    print("\n⚡ Paso 3: Ejecutando benchmark...")
    print("⏰ Tiempo estimado: 10-15 minutos")
    
    start_time = time.time()
    results_file = run_benchmark()
    end_time = time.time()
    
    if not results_file:
        print("❌ Error ejecutando el benchmark")
        return False
    
    duration = end_time - start_time
    print(f"✅ Benchmark completado en {duration/60:.1f} minutos")
    
    # Paso 4: Generar visualizaciones
    print("\n📊 Paso 4: Generando visualizaciones...")
    if not generate_visualizations(results_file):
        print("⚠️ Error generando visualizaciones, pero los datos están disponibles")
    else:
        print("✅ Visualizaciones generadas correctamente")
    
    # Paso 5: Crear reporte HTML
    print("\n📄 Paso 5: Creando reporte completo...")
    html_report = create_full_report(results_file)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("🎉 BENCHMARK COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    print(f"📊 Resultados JSON: {results_file}")
    print(f"📈 Gráficos: benchmark_plots/")
    if html_report:
        print(f"📄 Reporte HTML: {html_report}")
    print("=" * 60)
    
    return True

def quick_benchmark():
    """Versión rápida del benchmark para pruebas"""
    print("⚡ Ejecutando benchmark rápido...")
    
    # Configuración reducida para pruebas rápidas
    import sys
    sys.path.append(str(Path(__file__).parent))
    
    from benchmark_script import BenchmarkConfig, BenchmarkRunner
    import asyncio
    
    # Modificar configuración para ser más rápida
    class QuickBenchmarkConfig(BenchmarkConfig):
        TEST_DURATIONS = [10]  # Solo 10 segundos
        CONCURRENT_USERS = [1, 5, 10]  # Menos usuarios
        ENDPOINTS = ["/health", "/stats/basic"]  # Solo endpoints básicos
    
    async def run_quick():
        runner = BenchmarkRunner()
        runner.config = QuickBenchmarkConfig()
        
        await runner.run_all_benchmarks()
        results_file = runner.save_results("quick_benchmark_results.json")
        runner.generate_report()
        return results_file
    
    try:
        results_file = asyncio.run(run_quick())
        print(f"✅ Benchmark rápido completado: {results_file}")
        return results_file
    except Exception as e:
        print(f"❌ Error en benchmark rápido: {e}")
        return None

def show_help():
    """Muestra ayuda del script"""
    print("""
🚀 Sistema de Benchmark - ms_stats

USO:
    python run_benchmark.py [opción]

OPCIONES:
    (sin parámetros)  - Ejecuta benchmark completo
    --quick          - Ejecuta benchmark rápido (para pruebas)
    --check          - Solo verifica servicios
    --help           - Muestra esta ayuda

DESCRIPCIÓN:
    Este script automatiza todo el proceso de benchmark entre las dos
    implementaciones del microservicio ms_stats:
    
    • Ray Serve (Paralelo) - Puerto 8001
    • Flask (Secuencial) - Puerto 8002

PRERREQUISITOS:
    1. Ambos servicios deben estar corriendo
    2. Los servicios deben tener datos cargados
    3. Dependencias Python instaladas

SALIDAS:
    • benchmark_results_YYYYMMDD_HHMMSS.json - Datos raw
    • benchmark_plots/ - Gráficos PNG
    • benchmark_report.html - Reporte completo

EJEMPLO:
    # Benchmark completo
    python run_benchmark.py
    
    # Benchmark rápido para pruebas
    python run_benchmark.py --quick
    
    # Solo verificar servicios
    python run_benchmark.py --check
    """)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        option = sys.argv[1]
        
        if option == "--help" or option == "-h":
            show_help()
        elif option == "--quick":
            print("⚡ Modo rápido activado")
            results = quick_benchmark()
            if results:
                generate_visualizations(results)
        elif option == "--check":
            print("🔍 Verificando servicios solamente...")
            if check_dependencies() and check_services():
                print("✅ Todo listo para ejecutar benchmark")
            else:
                print("❌ Hay problemas que resolver antes del benchmark")
        else:
            print(f"❌ Opción desconocida: {option}")
            print("💡 Usa --help para ver opciones disponibles")
    else:
        # Ejecutar benchmark completo
        success = main()
        if not success:
            sys.exit(1)