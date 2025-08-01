#!/usr/bin/env python3
"""
Benchmark script para comparar el rendimiento entre:
- ms_stats con Ray Serve (paralelo) - Puerto 8001
- ms_stats con Flask (secuencial) - Puerto 8002

Este script mide:
- Latencia promedio
- Throughput (peticiones por segundo)
- Uso de memoria
- Uso de CPU
- Tiempo de respuesta bajo diferentes cargas de trabajo
"""

import asyncio
import aiohttp
import requests
import time
import statistics
import concurrent.futures
import threading
from datetime import datetime
import json
import psutil
import os
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
import numpy as np

class BenchmarkConfig:
    """Configuración del benchmark"""
    # URLs de los servicios
    RAY_SERVE_URL = "http://localhost:8001"  # Versión paralela
    FLASK_URL = "http://localhost:8002"      # Versión secuencial
    
    # Configuración de pruebas
    WARMUP_REQUESTS = 10        # Peticiones de calentamiento
    TEST_DURATIONS = [30, 60]   # Duración de pruebas en segundos
    CONCURRENT_USERS = [1, 5, 10, 20, 50]  # Diferentes niveles de concurrencia
    
    # Endpoints a probar
    ENDPOINTS = [
        "/health",
        "/stats/basic", 
        "/stats/summary",
        "/stats/prices",
        "/stats/by_ticker/AAPL"
    ]

class ServiceMonitor:
    """Monitor para recopilar métricas del sistema"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.cpu_samples = []
        self.memory_samples = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Inicia el monitoreo del sistema"""
        self.monitoring = True
        self.cpu_samples = []
        self.memory_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Detiene el monitoreo y retorna métricas"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        return {
            'cpu_avg': statistics.mean(self.cpu_samples) if self.cpu_samples else 0,
            'cpu_max': max(self.cpu_samples) if self.cpu_samples else 0,
            'memory_avg': statistics.mean(self.memory_samples) if self.memory_samples else 0,
            'memory_max': max(self.memory_samples) if self.memory_samples else 0,
            'samples': len(self.cpu_samples)
        }
    
    def _monitor_loop(self):
        """Loop de monitoreo en thread separado"""
        while self.monitoring:
            try:
                # Obtener métricas del sistema
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_info = psutil.virtual_memory()
                
                self.cpu_samples.append(cpu_percent)
                self.memory_samples.append(memory_info.percent)
                
                time.sleep(0.5)  # Muestrear cada 500ms
            except Exception as e:
                print(f"Error en monitoreo: {e}")
                break

class LoadTester:
    """Generador de carga para probar los servicios"""
    
    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url
        self.service_name = service_name
        self.session = None
    
    async def setup_session(self):
        """Configura la sesión HTTP asíncrona"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout
        )
    
    async def cleanup_session(self):
        """Limpia la sesión HTTP"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, endpoint: str) -> Tuple[float, int, bool]:
        """
        Realiza una petición HTTP y mide el tiempo de respuesta
        Returns: (response_time, status_code, success)
        """
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                await response.text()  # Leer la respuesta completa
                end_time = time.time()
                return (end_time - start_time, response.status, response.status == 200)
        except Exception as e:
            end_time = time.time()
            return (end_time - start_time, 0, False)
    
    async def warmup(self, endpoint: str, num_requests: int = 10):
        """Calentamiento del servicio"""
        print(f"🔥 Calentando {self.service_name} con {num_requests} peticiones...")
        tasks = []
        for _ in range(num_requests):
            tasks.append(self.make_request(endpoint))
        
        await asyncio.gather(*tasks)
        print(f"✅ Calentamiento de {self.service_name} completado")
    
    async def load_test(self, endpoint: str, concurrent_users: int, duration: int) -> Dict[str, Any]:
        """
        Ejecuta una prueba de carga
        """
        print(f"🚀 Iniciando prueba: {self.service_name} - {endpoint} - {concurrent_users} usuarios - {duration}s")
        
        response_times = []
        status_codes = []
        errors = 0
        total_requests = 0
        
        start_time = time.time()
        end_time = start_time + duration
        
        async def worker():
            nonlocal total_requests, errors
            while time.time() < end_time:
                response_time, status_code, success = await self.make_request(endpoint)
                response_times.append(response_time)
                status_codes.append(status_code)
                total_requests += 1
                
                if not success:
                    errors += 1
                
                # Pequeña pausa para evitar saturar completamente
                await asyncio.sleep(0.001)
        
        # Crear workers concurrentes
        tasks = [worker() for _ in range(concurrent_users)]
        await asyncio.gather(*tasks)
        
        # Calcular métricas
        actual_duration = time.time() - start_time
        
        if response_times:
            return {
                'service': self.service_name,
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'duration': actual_duration,
                'total_requests': total_requests,
                'successful_requests': total_requests - errors,
                'failed_requests': errors,
                'requests_per_second': total_requests / actual_duration,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'p50_response_time': statistics.median(response_times),
                'p95_response_time': np.percentile(response_times, 95),
                'p99_response_time': np.percentile(response_times, 99),
                'error_rate': (errors / total_requests) * 100 if total_requests > 0 else 0
            }
        else:
            return {
                'service': self.service_name,
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'duration': actual_duration,
                'error': 'No se completaron peticiones exitosas'
            }

class BenchmarkRunner:
    """Ejecutor principal del benchmark"""
    
    def __init__(self):
        self.config = BenchmarkConfig()
        self.results = []
        
    def check_services_availability(self):
        """Verifica que ambos servicios estén disponibles"""
        print("🔍 Verificando disponibilidad de servicios...")
        
        services = [
            ("Ray Serve (Paralelo)", self.config.RAY_SERVE_URL),
            ("Flask (Secuencial)", self.config.FLASK_URL)
        ]
        
        for service_name, url in services:
            try:
                response = requests.get(f"{url}/health", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {service_name}: OK - {data.get('records', 0)} registros")
                else:
                    print(f"❌ {service_name}: Error HTTP {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ {service_name}: No disponible - {e}")
                return False
        
        return True
    
    async def run_single_benchmark(self, service_url: str, service_name: str, 
                                 endpoint: str, concurrent_users: int, duration: int):
        """Ejecuta un benchmark individual"""
        
        # Configurar tester
        tester = LoadTester(service_url, service_name)
        await tester.setup_session()
        
        # Configurar monitor del sistema
        monitor = ServiceMonitor(service_name)
        
        try:
            # Calentamiento
            await tester.warmup(endpoint, self.config.WARMUP_REQUESTS)
            
            # Iniciar monitoreo
            monitor.start_monitoring()
            
            # Ejecutar prueba de carga
            result = await tester.load_test(endpoint, concurrent_users, duration)
            
            # Detener monitoreo
            system_metrics = monitor.stop_monitoring()
            
            # Agregar métricas del sistema al resultado
            result.update({
                'system_cpu_avg': system_metrics['cpu_avg'],
                'system_cpu_max': system_metrics['cpu_max'],
                'system_memory_avg': system_metrics['memory_avg'],
                'system_memory_max': system_metrics['memory_max']
            })
            
            return result
            
        finally:
            await tester.cleanup_session()
    
    async def run_all_benchmarks(self):
        """Ejecuta todos los benchmarks configurados"""
        print("🏁 Iniciando benchmark completo...")
        
        services = [
            (self.config.RAY_SERVE_URL, "Ray Serve (Paralelo)"),
            (self.config.FLASK_URL, "Flask (Secuencial)")
        ]
        
        for service_url, service_name in services:
            for endpoint in self.config.ENDPOINTS:
                for concurrent_users in self.config.CONCURRENT_USERS:
                    for duration in self.config.TEST_DURATIONS:
                        result = await self.run_single_benchmark(
                            service_url, service_name, endpoint, 
                            concurrent_users, duration
                        )
                        self.results.append(result)
                        
                        # Pausa entre pruebas para estabilizar el sistema
                        await asyncio.sleep(2)
    
    def save_results(self, filename: str = None):
        """Guarda los resultados en un archivo JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📊 Resultados guardados en: {filename}")
        return filename
    
    def generate_report(self):
        """Genera un reporte de los resultados"""
        if not self.results:
            print("❌ No hay resultados para generar reporte")
            return
        
        print("\n" + "="*80)
        print("📊 REPORTE DE BENCHMARK - ms_stats")
        print("="*80)
        
        # Agrupar resultados por servicio
        ray_results = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_results = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        print(f"\n🔍 Resumen General:")
        print(f"   • Total de pruebas ejecutadas: {len(self.results)}")
        print(f"   • Pruebas Ray Serve: {len(ray_results)}")
        print(f"   • Pruebas Flask: {len(flask_results)}")
        
        # Comparación de rendimiento promedio
        self._compare_services(ray_results, flask_results)
        
        # Análisis por endpoint
        self._analyze_by_endpoint()
        
        # Análisis por concurrencia
        self._analyze_by_concurrency()
        
        print("\n" + "="*80)
    
    def _compare_services(self, ray_results: List[Dict], flask_results: List[Dict]):
        """Compara el rendimiento general entre servicios"""
        print(f"\n🏆 Comparación de Servicios:")
        
        if ray_results and flask_results:
            ray_avg_rps = statistics.mean([r.get('requests_per_second', 0) for r in ray_results])
            flask_avg_rps = statistics.mean([r.get('requests_per_second', 0) for r in flask_results])
            
            ray_avg_latency = statistics.mean([r.get('avg_response_time', 0) for r in ray_results])
            flask_avg_latency = statistics.mean([r.get('avg_response_time', 0) for r in flask_results])
            
            print(f"   Ray Serve (Paralelo):")
            print(f"     • RPS promedio: {ray_avg_rps:.2f}")
            print(f"     • Latencia promedio: {ray_avg_latency*1000:.2f}ms")
            
            print(f"   Flask (Secuencial):")
            print(f"     • RPS promedio: {flask_avg_rps:.2f}")
            print(f"     • Latencia promedio: {flask_avg_latency*1000:.2f}ms")
            
            # Comparación
            rps_improvement = ((ray_avg_rps - flask_avg_rps) / flask_avg_rps) * 100
            latency_improvement = ((flask_avg_latency - ray_avg_latency) / flask_avg_latency) * 100
            
            print(f"\n   📈 Mejoras de Ray Serve vs Flask:")
            print(f"     • Throughput: {rps_improvement:+.1f}%")
            print(f"     • Latencia: {latency_improvement:+.1f}%")
    
    def _analyze_by_endpoint(self):
        """Analiza rendimiento por endpoint"""
        print(f"\n📋 Análisis por Endpoint:")
        
        endpoints = set(r.get('endpoint', '') for r in self.results)
        
        for endpoint in sorted(endpoints):
            endpoint_results = [r for r in self.results if r.get('endpoint') == endpoint]
            
            if endpoint_results:
                avg_rps = statistics.mean([r.get('requests_per_second', 0) for r in endpoint_results])
                avg_latency = statistics.mean([r.get('avg_response_time', 0) for r in endpoint_results])
                
                print(f"   {endpoint}:")
                print(f"     • RPS promedio: {avg_rps:.2f}")
                print(f"     • Latencia promedio: {avg_latency*1000:.2f}ms")
    
    def _analyze_by_concurrency(self):
        """Analiza rendimiento por nivel de concurrencia"""
        print(f"\n👥 Análisis por Concurrencia:")
        
        concurrency_levels = set(r.get('concurrent_users', 0) for r in self.results)
        
        for level in sorted(concurrency_levels):
            level_results = [r for r in self.results if r.get('concurrent_users') == level]
            
            if level_results:
                ray_results = [r for r in level_results if 'Ray Serve' in r.get('service', '')]
                flask_results = [r for r in level_results if 'Flask' in r.get('service', '')]
                
                print(f"   {level} usuarios concurrentes:")
                
                if ray_results:
                    ray_avg_rps = statistics.mean([r.get('requests_per_second', 0) for r in ray_results])
                    print(f"     • Ray Serve: {ray_avg_rps:.2f} RPS")
                
                if flask_results:
                    flask_avg_rps = statistics.mean([r.get('requests_per_second', 0) for r in flask_results])
                    print(f"     • Flask: {flask_avg_rps:.2f} RPS")

async def main():
    """Función principal"""
    print("🚀 Iniciando Benchmark de ms_stats")
    print("   Comparando Ray Serve (Paralelo) vs Flask (Secuencial)")
    print("-" * 60)
    
    runner = BenchmarkRunner()
    
    # Verificar servicios
    if not runner.check_services_availability():
        print("❌ No se pueden ejecutar los benchmarks. Verifica que ambos servicios estén corriendo.")
        return
    
    print("✅ Ambos servicios están disponibles")
    print("⏳ Iniciando benchmarks (esto puede tomar varios minutos)...")
    
    # Ejecutar benchmarks
    await runner.run_all_benchmarks()
    
    # Guardar resultados
    results_file = runner.save_results()
    
    # Generar reporte
    runner.generate_report()
    
    print(f"\n✅ Benchmark completado!")
    print(f"📁 Resultados detallados en: {results_file}")

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import aiohttp
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("💡 Instala con: pip install aiohttp matplotlib numpy psutil")
        exit(1)
    
    # Ejecutar benchmark
    asyncio.run(main())