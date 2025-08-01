#!/usr/bin/env python3
"""
Script para generar visualizaciones de los resultados del benchmark
"""

import json
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path
import argparse
import pandas as pd
from datetime import datetime

class BenchmarkVisualizer:
    """Generador de visualizaciones para resultados de benchmark"""
    
    def __init__(self, results_file: str):
        self.results_file = results_file
        self.results = self.load_results()
        self.setup_plotting()
    
    def load_results(self):
        """Carga los resultados del benchmark"""
        try:
            with open(self.results_file, 'r') as f:
                results = json.load(f)
            print(f"✅ Cargados {len(results)} resultados de {self.results_file}")
            return results
        except Exception as e:
            print(f"❌ Error cargando resultados: {e}")
            return []
    
    def setup_plotting(self):
        """Configura el estilo de los gráficos"""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
    
    def create_comparison_plots(self):
        """Crea todos los gráficos de comparación"""
        if not self.results:
            print("❌ No hay resultados para visualizar")
            return
        
        # Crear directorio para gráficos
        output_dir = Path("benchmark_plots")
        output_dir.mkdir(exist_ok=True)
        
        # Generar diferentes tipos de gráficos
        self.plot_throughput_comparison(output_dir)
        self.plot_latency_comparison(output_dir)
        self.plot_concurrency_scaling(output_dir)
        self.plot_endpoint_performance(output_dir)
        self.plot_system_resources(output_dir)
        self.plot_error_rates(output_dir)
        
        print(f"📊 Gráficos generados en: {output_dir}")
    
    def plot_throughput_comparison(self, output_dir: Path):
        """Gráfico de comparación de throughput (RPS)"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Preparar datos
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        # Gráfico por concurrencia
        concurrency_levels = sorted(set(r.get('concurrent_users', 0) for r in self.results))
        ray_rps_by_concurrency = []
        flask_rps_by_concurrency = []
        
        for level in concurrency_levels:
            ray_level = [r.get('requests_per_second', 0) for r in ray_data 
                        if r.get('concurrent_users') == level]
            flask_level = [r.get('requests_per_second', 0) for r in flask_data 
                          if r.get('concurrent_users') == level]
            
            ray_rps_by_concurrency.append(np.mean(ray_level) if ray_level else 0)
            flask_rps_by_concurrency.append(np.mean(flask_level) if flask_level else 0)
        
        # Plot por concurrencia
        x = np.arange(len(concurrency_levels))
        width = 0.35
        
        ax1.bar(x - width/2, ray_rps_by_concurrency, width, label='Ray Serve (Paralelo)', 
                color='#2E86AB', alpha=0.8)
        ax1.bar(x + width/2, flask_rps_by_concurrency, width, label='Flask (Secuencial)', 
                color='#A23B72', alpha=0.8)
        
        ax1.set_xlabel('Usuarios Concurrentes')
        ax1.set_ylabel('Requests per Second (RPS)')
        ax1.set_title('Throughput por Nivel de Concurrencia')
        ax1.set_xticks(x)
        ax1.set_xticklabels(concurrency_levels)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Gráfico por endpoint
        endpoints = sorted(set(r.get('endpoint', '') for r in self.results))
        ray_rps_by_endpoint = []
        flask_rps_by_endpoint = []
        
        for endpoint in endpoints:
            ray_endpoint = [r.get('requests_per_second', 0) for r in ray_data 
                           if r.get('endpoint') == endpoint]
            flask_endpoint = [r.get('requests_per_second', 0) for r in flask_data 
                             if r.get('endpoint') == endpoint]
            
            ray_rps_by_endpoint.append(np.mean(ray_endpoint) if ray_endpoint else 0)
            flask_rps_by_endpoint.append(np.mean(flask_endpoint) if flask_endpoint else 0)
        
        x2 = np.arange(len(endpoints))
        ax2.bar(x2 - width/2, ray_rps_by_endpoint, width, label='Ray Serve (Paralelo)', 
                color='#2E86AB', alpha=0.8)
        ax2.bar(x2 + width/2, flask_rps_by_endpoint, width, label='Flask (Secuencial)', 
                color='#A23B72', alpha=0.8)
        
        ax2.set_xlabel('Endpoint')
        ax2.set_ylabel('Requests per Second (RPS)')
        ax2.set_title('Throughput por Endpoint')
        ax2.set_xticks(x2)
        ax2.set_xticklabels([ep.split('/')[-1] for ep in endpoints], rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'throughput_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_latency_comparison(self, output_dir: Path):
        """Gráfico de comparación de latencia"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        # Métricas de latencia
        latency_metrics = ['avg_response_time', 'p50_response_time', 'p95_response_time', 'p99_response_time']
        metric_names = ['Promedio', 'P50', 'P95', 'P99']
        
        concurrency_levels = sorted(set(r.get('concurrent_users', 0) for r in self.results))
        
        for i, (metric, name) in enumerate(zip(latency_metrics, metric_names)):
            ax = [ax1, ax2, ax3, ax4][i]
            
            ray_latencies = []
            flask_latencies = []
            
            for level in concurrency_levels:
                ray_level = [r.get(metric, 0) * 1000 for r in ray_data 
                            if r.get('concurrent_users') == level and r.get(metric)]
                flask_level = [r.get(metric, 0) * 1000 for r in flask_data 
                              if r.get('concurrent_users') == level and r.get(metric)]
                
                ray_latencies.append(np.mean(ray_level) if ray_level else 0)
                flask_latencies.append(np.mean(flask_level) if flask_level else 0)
            
            ax.plot(concurrency_levels, ray_latencies, 'o-', label='Ray Serve (Paralelo)', 
                   color='#2E86AB', linewidth=2, markersize=6)
            ax.plot(concurrency_levels, flask_latencies, 's-', label='Flask (Secuencial)', 
                   color='#A23B72', linewidth=2, markersize=6)
            
            ax.set_xlabel('Usuarios Concurrentes')
            ax.set_ylabel('Latencia (ms)')
            ax.set_title(f'Latencia {name}')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'latency_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_concurrency_scaling(self, output_dir: Path):
        """Gráfico de escalabilidad con concurrencia"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        concurrency_levels = sorted(set(r.get('concurrent_users', 0) for r in self.results))
        
        # Escalabilidad de throughput
        ray_rps = []
        flask_rps = []
        ray_rps_std = []
        flask_rps_std = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('requests_per_second', 0) for r in ray_data 
                       if r.get('concurrent_users') == level]
            flask_vals = [r.get('requests_per_second', 0) for r in flask_data 
                         if r.get('concurrent_users') == level]
            
            ray_rps.append(np.mean(ray_vals) if ray_vals else 0)
            flask_rps.append(np.mean(flask_vals) if flask_vals else 0)
            ray_rps_std.append(np.std(ray_vals) if len(ray_vals) > 1 else 0)
            flask_rps_std.append(np.std(flask_vals) if len(flask_vals) > 1 else 0)
        
        ax1.errorbar(concurrency_levels, ray_rps, yerr=ray_rps_std, 
                    label='Ray Serve (Paralelo)', color='#2E86AB', 
                    linewidth=2, marker='o', capsize=5)
        ax1.errorbar(concurrency_levels, flask_rps, yerr=flask_rps_std, 
                    label='Flask (Secuencial)', color='#A23B72', 
                    linewidth=2, marker='s', capsize=5)
        
        ax1.set_xlabel('Usuarios Concurrentes')
        ax1.set_ylabel('Requests per Second (RPS)')
        ax1.set_title('Escalabilidad del Throughput')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Escalabilidad de latencia promedio
        ray_latency = []
        flask_latency = []
        ray_latency_std = []
        flask_latency_std = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('avg_response_time', 0) * 1000 for r in ray_data 
                       if r.get('concurrent_users') == level and r.get('avg_response_time')]
            flask_vals = [r.get('avg_response_time', 0) * 1000 for r in flask_data 
                         if r.get('concurrent_users') == level and r.get('avg_response_time')]
            
            ray_latency.append(np.mean(ray_vals) if ray_vals else 0)
            flask_latency.append(np.mean(flask_vals) if flask_vals else 0)
            ray_latency_std.append(np.std(ray_vals) if len(ray_vals) > 1 else 0)
            flask_latency_std.append(np.std(flask_vals) if len(flask_vals) > 1 else 0)
        
        ax2.errorbar(concurrency_levels, ray_latency, yerr=ray_latency_std, 
                    label='Ray Serve (Paralelo)', color='#2E86AB', 
                    linewidth=2, marker='o', capsize=5)
        ax2.errorbar(concurrency_levels, flask_latency, yerr=flask_latency_std, 
                    label='Flask (Secuencial)', color='#A23B72', 
                    linewidth=2, marker='s', capsize=5)
        
        ax2.set_xlabel('Usuarios Concurrentes')
        ax2.set_ylabel('Latencia Promedio (ms)')
        ax2.set_title('Escalabilidad de la Latencia')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'concurrency_scaling.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_endpoint_performance(self, output_dir: Path):
        """Gráfico de rendimiento por endpoint"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        endpoints = sorted(set(r.get('endpoint', '') for r in self.results))
        
        # Preparar datos por endpoint
        endpoint_data = {}
        for endpoint in endpoints:
            endpoint_data[endpoint] = {
                'ray': [r for r in self.results if 'Ray Serve' in r.get('service', '') and r.get('endpoint') == endpoint],
                'flask': [r for r in self.results if 'Flask' in r.get('service', '') and r.get('endpoint') == endpoint]
            }
        
        # Gráfico 1: RPS por endpoint
        ray_rps = []
        flask_rps = []
        endpoint_labels = []
        
        for endpoint in endpoints:
            if endpoint_data[endpoint]['ray'] or endpoint_data[endpoint]['flask']:
                ray_vals = [r.get('requests_per_second', 0) for r in endpoint_data[endpoint]['ray']]
                flask_vals = [r.get('requests_per_second', 0) for r in endpoint_data[endpoint]['flask']]
                
                ray_rps.append(np.mean(ray_vals) if ray_vals else 0)
                flask_rps.append(np.mean(flask_vals) if flask_vals else 0)
                endpoint_labels.append(endpoint.split('/')[-1])
        
        x = np.arange(len(endpoint_labels))
        width = 0.35
        
        ax1.bar(x - width/2, ray_rps, width, label='Ray Serve', color='#2E86AB', alpha=0.8)
        ax1.bar(x + width/2, flask_rps, width, label='Flask', color='#A23B72', alpha=0.8)
        ax1.set_xlabel('Endpoint')
        ax1.set_ylabel('RPS Promedio')
        ax1.set_title('Throughput por Endpoint')
        ax1.set_xticks(x)
        ax1.set_xticklabels(endpoint_labels, rotation=45)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Gráfico 2: Latencia promedio por endpoint
        ray_latency = []
        flask_latency = []
        
        for endpoint in endpoints:
            if endpoint_data[endpoint]['ray'] or endpoint_data[endpoint]['flask']:
                ray_vals = [r.get('avg_response_time', 0) * 1000 for r in endpoint_data[endpoint]['ray'] 
                           if r.get('avg_response_time')]
                flask_vals = [r.get('avg_response_time', 0) * 1000 for r in endpoint_data[endpoint]['flask'] 
                             if r.get('avg_response_time')]
                
                ray_latency.append(np.mean(ray_vals) if ray_vals else 0)
                flask_latency.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax2.bar(x - width/2, ray_latency, width, label='Ray Serve', color='#2E86AB', alpha=0.8)
        ax2.bar(x + width/2, flask_latency, width, label='Flask', color='#A23B72', alpha=0.8)
        ax2.set_xlabel('Endpoint')
        ax2.set_ylabel('Latencia Promedio (ms)')
        ax2.set_title('Latencia por Endpoint')
        ax2.set_xticks(x)
        ax2.set_xticklabels(endpoint_labels, rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Gráfico 3: P95 por endpoint
        ray_p95 = []
        flask_p95 = []
        
        for endpoint in endpoints:
            if endpoint_data[endpoint]['ray'] or endpoint_data[endpoint]['flask']:
                ray_vals = [r.get('p95_response_time', 0) * 1000 for r in endpoint_data[endpoint]['ray'] 
                           if r.get('p95_response_time')]
                flask_vals = [r.get('p95_response_time', 0) * 1000 for r in endpoint_data[endpoint]['flask'] 
                             if r.get('p95_response_time')]
                
                ray_p95.append(np.mean(ray_vals) if ray_vals else 0)
                flask_p95.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax3.bar(x - width/2, ray_p95, width, label='Ray Serve', color='#2E86AB', alpha=0.8)
        ax3.bar(x + width/2, flask_p95, width, label='Flask', color='#A23B72', alpha=0.8)
        ax3.set_xlabel('Endpoint')
        ax3.set_ylabel('Latencia P95 (ms)')
        ax3.set_title('Latencia P95 por Endpoint')
        ax3.set_xticks(x)
        ax3.set_xticklabels(endpoint_labels, rotation=45)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Gráfico 4: Tasa de error por endpoint
        ray_errors = []
        flask_errors = []
        
        for endpoint in endpoints:
            if endpoint_data[endpoint]['ray'] or endpoint_data[endpoint]['flask']:
                ray_vals = [r.get('error_rate', 0) * 100 for r in endpoint_data[endpoint]['ray']]
                flask_vals = [r.get('error_rate', 0) * 100 for r in endpoint_data[endpoint]['flask']]
                
                ray_errors.append(np.mean(ray_vals) if ray_vals else 0)
                flask_errors.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax4.bar(x - width/2, ray_errors, width, label='Ray Serve', color='#2E86AB', alpha=0.8)
        ax4.bar(x + width/2, flask_errors, width, label='Flask', color='#A23B72', alpha=0.8)
        ax4.set_xlabel('Endpoint')
        ax4.set_ylabel('Tasa de Error (%)')
        ax4.set_title('Tasa de Error por Endpoint')
        ax4.set_xticks(x)
        ax4.set_xticklabels(endpoint_labels, rotation=45)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'endpoint_performance.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_system_resources(self, output_dir: Path):
        """Gráfico de uso de recursos del sistema"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        concurrency_levels = sorted(set(r.get('concurrent_users', 0) for r in self.results))
        
        # CPU Usage
        ray_cpu = []
        flask_cpu = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('cpu_usage', 0) for r in ray_data 
                       if r.get('concurrent_users') == level and r.get('cpu_usage')]
            flask_vals = [r.get('cpu_usage', 0) for r in flask_data 
                         if r.get('concurrent_users') == level and r.get('cpu_usage')]
            
            ray_cpu.append(np.mean(ray_vals) if ray_vals else 0)
            flask_cpu.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax1.plot(concurrency_levels, ray_cpu, 'o-', label='Ray Serve', 
                color='#2E86AB', linewidth=2, markersize=6)
        ax1.plot(concurrency_levels, flask_cpu, 's-', label='Flask', 
                color='#A23B72', linewidth=2, markersize=6)
        ax1.set_xlabel('Usuarios Concurrentes')
        ax1.set_ylabel('Uso de CPU (%)')
        ax1.set_title('Uso de CPU')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Memory Usage
        ray_memory = []
        flask_memory = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('memory_usage', 0) for r in ray_data 
                       if r.get('concurrent_users') == level and r.get('memory_usage')]
            flask_vals = [r.get('memory_usage', 0) for r in flask_data 
                         if r.get('concurrent_users') == level and r.get('memory_usage')]
            
            ray_memory.append(np.mean(ray_vals) if ray_vals else 0)
            flask_memory.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax2.plot(concurrency_levels, ray_memory, 'o-', label='Ray Serve', 
                color='#2E86AB', linewidth=2, markersize=6)
        ax2.plot(concurrency_levels, flask_memory, 's-', label='Flask', 
                color='#A23B72', linewidth=2, markersize=6)
        ax2.set_xlabel('Usuarios Concurrentes')
        ax2.set_ylabel('Uso de Memoria (MB)')
        ax2.set_title('Uso de Memoria')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Disk I/O
        ray_disk = []
        flask_disk = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('disk_io', 0) for r in ray_data 
                       if r.get('concurrent_users') == level and r.get('disk_io')]
            flask_vals = [r.get('disk_io', 0) for r in flask_data 
                         if r.get('concurrent_users') == level and r.get('disk_io')]
            
            ray_disk.append(np.mean(ray_vals) if ray_vals else 0)
            flask_disk.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax3.plot(concurrency_levels, ray_disk, 'o-', label='Ray Serve', 
                color='#2E86AB', linewidth=2, markersize=6)
        ax3.plot(concurrency_levels, flask_disk, 's-', label='Flask', 
                color='#A23B72', linewidth=2, markersize=6)
        ax3.set_xlabel('Usuarios Concurrentes')
        ax3.set_ylabel('Disk I/O (MB/s)')
        ax3.set_title('Uso de Disco')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Network I/O
        ray_network = []
        flask_network = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('network_io', 0) for r in ray_data 
                       if r.get('concurrent_users') == level and r.get('network_io')]
            flask_vals = [r.get('network_io', 0) for r in flask_data 
                         if r.get('concurrent_users') == level and r.get('network_io')]
            
            ray_network.append(np.mean(ray_vals) if ray_vals else 0)
            flask_network.append(np.mean(flask_vals) if flask_vals else 0)
        
        ax4.plot(concurrency_levels, ray_network, 'o-', label='Ray Serve', 
                color='#2E86AB', linewidth=2, markersize=6)
        ax4.plot(concurrency_levels, flask_network, 's-', label='Flask', 
                color='#A23B72', linewidth=2, markersize=6)
        ax4.set_xlabel('Usuarios Concurrentes')
        ax4.set_ylabel('Network I/O (MB/s)')
        ax4.set_title('Uso de Red')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'system_resources.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_error_rates(self, output_dir: Path):
        """Gráfico de tasas de error"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        # Error rates por concurrencia
        concurrency_levels = sorted(set(r.get('concurrent_users', 0) for r in self.results))
        ray_errors = []
        flask_errors = []
        
        for level in concurrency_levels:
            ray_vals = [r.get('error_rate', 0) * 100 for r in ray_data 
                       if r.get('concurrent_users') == level]
            flask_vals = [r.get('error_rate', 0) * 100 for r in flask_data 
                         if r.get('concurrent_users') == level]
            
            ray_errors.append(np.mean(ray_vals) if ray_vals else 0)
            flask_errors.append(np.mean(flask_vals) if flask_vals else 0)
        
        x = np.arange(len(concurrency_levels))
        width = 0.35
        
        ax1.bar(x - width/2, ray_errors, width, label='Ray Serve', 
                color='#2E86AB', alpha=0.8)
        ax1.bar(x + width/2, flask_errors, width, label='Flask', 
                color='#A23B72', alpha=0.8)
        
        ax1.set_xlabel('Usuarios Concurrentes')
        ax1.set_ylabel('Tasa de Error (%)')
        ax1.set_title('Tasa de Error por Concurrencia')
        ax1.set_xticks(x)
        ax1.set_xticklabels(concurrency_levels)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Distribución de códigos de error
        ray_errors_by_code = {}
        flask_errors_by_code = {}
        
        for result in ray_data:
            errors = result.get('error_codes', {})
            for code, count in errors.items():
                ray_errors_by_code[code] = ray_errors_by_code.get(code, 0) + count
        
        for result in flask_data:
            errors = result.get('error_codes', {})
            for code, count in errors.items():
                flask_errors_by_code[code] = flask_errors_by_code.get(code, 0) + count
        
        # Crear gráfico de barras apiladas para códigos de error
        error_codes = sorted(set(list(ray_errors_by_code.keys()) + list(flask_errors_by_code.keys())))
        
        if error_codes:
            ray_counts = [ray_errors_by_code.get(code, 0) for code in error_codes]
            flask_counts = [flask_errors_by_code.get(code, 0) for code in error_codes]
            
            x2 = np.arange(len(error_codes))
            ax2.bar(x2 - width/2, ray_counts, width, label='Ray Serve', 
                    color='#2E86AB', alpha=0.8)
            ax2.bar(x2 + width/2, flask_counts, width, label='Flask', 
                    color='#A23B72', alpha=0.8)
            
            ax2.set_xlabel('Código de Error HTTP')
            ax2.set_ylabel('Número de Errores')
            ax2.set_title('Distribución de Códigos de Error')
            ax2.set_xticks(x2)
            ax2.set_xticklabels(error_codes)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No hay errores registrados', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax2.transAxes, fontsize=14)
            ax2.set_title('Distribución de Códigos de Error')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'error_rates.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_summary_report(self, output_dir: Path):
        """Genera un reporte resumen de los resultados"""
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        # Calcular estadísticas generales
        ray_avg_rps = np.mean([r.get('requests_per_second', 0) for r in ray_data]) if ray_data else 0
        flask_avg_rps = np.mean([r.get('requests_per_second', 0) for r in flask_data]) if flask_data else 0
        
        ray_avg_latency = np.mean([r.get('avg_response_time', 0) * 1000 for r in ray_data 
                                  if r.get('avg_response_time')]) if ray_data else 0
        flask_avg_latency = np.mean([r.get('avg_response_time', 0) * 1000 for r in flask_data 
                                    if r.get('avg_response_time')]) if flask_data else 0
        
        ray_avg_errors = np.mean([r.get('error_rate', 0) * 100 for r in ray_data]) if ray_data else 0
        flask_avg_errors = np.mean([r.get('error_rate', 0) * 100 for r in flask_data]) if flask_data else 0
        
        # Generar reporte
        report = f"""
# Reporte de Benchmark - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Resumen Ejecutivo

### Throughput (RPS)
- **Ray Serve (Paralelo)**: {ray_avg_rps:.2f} RPS promedio
- **Flask (Secuencial)**: {flask_avg_rps:.2f} RPS promedio
- **Mejora**: {((ray_avg_rps - flask_avg_rps) / flask_avg_rps * 100):.1f}% {'mayor' if ray_avg_rps > flask_avg_rps else 'menor'} throughput con Ray Serve

### Latencia
- **Ray Serve (Paralelo)**: {ray_avg_latency:.2f} ms promedio
- **Flask (Secuencial)**: {flask_avg_latency:.2f} ms promedio
- **Mejora**: {((flask_avg_latency - ray_avg_latency) / flask_avg_latency * 100):.1f}% {'menor' if ray_avg_latency < flask_avg_latency else 'mayor'} latencia con Ray Serve

### Confiabilidad
- **Ray Serve (Paralelo)**: {ray_avg_errors:.2f}% tasa de error promedio
- **Flask (Secuencial)**: {flask_avg_errors:.2f}% tasa de error promedio

## Detalles de la Prueba
- **Total de pruebas ejecutadas**: {len(self.results)}
- **Pruebas con Ray Serve**: {len(ray_data)}
- **Pruebas con Flask**: {len(flask_data)}
- **Endpoints probados**: {len(set(r.get('endpoint', '') for r in self.results))}
- **Niveles de concurrencia**: {sorted(set(r.get('concurrent_users', 0) for r in self.results))}

## Conclusiones

### Ventajas de Ray Serve:
"""
        
        if ray_avg_rps > flask_avg_rps:
            report += f"- Mayor throughput: {ray_avg_rps:.1f} vs {flask_avg_rps:.1f} RPS\n"
        if ray_avg_latency < flask_avg_latency:
            report += f"- Menor latencia: {ray_avg_latency:.1f} vs {flask_avg_latency:.1f} ms\n"
        if ray_avg_errors < flask_avg_errors:
            report += f"- Menor tasa de error: {ray_avg_errors:.2f}% vs {flask_avg_errors:.2f}%\n"
        
        report += """
- Mejor escalabilidad con múltiples usuarios concurrentes
- Procesamiento paralelo de requests
- Mejor utilización de recursos del sistema

### Ventajas de Flask:
"""
        
        if flask_avg_rps > ray_avg_rps:
            report += f"- Mayor throughput: {flask_avg_rps:.1f} vs {ray_avg_rps:.1f} RPS\n"
        if flask_avg_latency < ray_avg_latency:
            report += f"- Menor latencia: {flask_avg_latency:.1f} vs {ray_avg_latency:.1f} ms\n"
        if flask_avg_errors < ray_avg_errors:
            report += f"- Menor tasa de error: {flask_avg_errors:.2f}% vs {ray_avg_errors:.2f}%\n"
        
        report += """
- Simplicidad de implementación y despliegue
- Menor overhead para cargas de trabajo simples
- Ecosistema más maduro y documentado

## Recomendaciones

"""
        
        if ray_avg_rps > flask_avg_rps * 1.2:  # 20% mejor
            report += "✅ **Se recomienda Ray Serve** para aplicaciones que requieren alto throughput\n"
        elif flask_avg_rps > ray_avg_rps * 1.2:
            report += "✅ **Se recomienda Flask** para aplicaciones simples con baja concurrencia\n"
        else:
            report += "⚖️ **Ambas opciones son viables** - la elección depende de otros factores como complejidad de despliegue\n"
        
        report += f"""
- Para cargas de trabajo con alta concurrencia (>{max(set(r.get('concurrent_users', 0) for r in self.results))//2} usuarios): Ray Serve
- Para aplicaciones simples con baja concurrencia: Flask
- Considerar Ray Serve para modelos de ML que requieren paralelización

## Archivos Generados
- `throughput_comparison.png`: Comparación de throughput
- `latency_comparison.png`: Análisis de latencia
- `concurrency_scaling.png`: Escalabilidad con concurrencia
- `endpoint_performance.png`: Rendimiento por endpoint
- `system_resources.png`: Uso de recursos del sistema
- `error_rates.png`: Análisis de errores
- `benchmark_report.md`: Este reporte
"""
        
        # Guardar reporte
        with open(output_dir / 'benchmark_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("📄 Reporte generado: benchmark_report.md")
    
    def create_interactive_dashboard(self, output_dir: Path):
        """Crea un dashboard HTML interactivo"""
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Benchmark - Ray Serve vs Flask</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2E86AB, #A23B72);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #2E86AB;
        }}
        .stat-card.flask {{
            border-left-color: #A23B72;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2E86AB;
            margin: 10px 0;
        }}
        .stat-card.flask .stat-value {{
            color: #A23B72;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .stat-service {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .charts-section {{
            padding: 30px;
            background: #f8f9fa;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart-container img {{
            width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        .chart-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }}
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
        }}
        .comparison-highlight {{
            background: linear-gradient(135deg, #e3f2fd, #f3e5f5);
            margin: 20px 30px;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        .comparison-highlight h3 {{
            margin-top: 0;
            color: #333;
        }}
        .winner {{
            color: #4caf50;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Benchmark Dashboard</h1>
            <p>Ray Serve vs Flask - Análisis de Rendimiento</p>
            <p>Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
"""
        
        # Calcular estadísticas para el dashboard
        ray_data = [r for r in self.results if 'Ray Serve' in r.get('service', '')]
        flask_data = [r for r in self.results if 'Flask' in r.get('service', '')]
        
        ray_avg_rps = np.mean([r.get('requests_per_second', 0) for r in ray_data]) if ray_data else 0
        flask_avg_rps = np.mean([r.get('requests_per_second', 0) for r in flask_data]) if flask_data else 0
        
        ray_avg_latency = np.mean([r.get('avg_response_time', 0) * 1000 for r in ray_data 
                                  if r.get('avg_response_time')]) if ray_data else 0
        flask_avg_latency = np.mean([r.get('avg_response_time', 0) * 1000 for r in flask_data 
                                    if r.get('avg_response_time')]) if flask_data else 0
        
        # Agregar cards de estadísticas
        html_content += f"""
            <div class="stat-card">
                <div class="stat-service">Ray Serve (Paralelo)</div>
                <div class="stat-value">{ray_avg_rps:.1f}</div>
                <div class="stat-label">RPS Promedio</div>
            </div>
            <div class="stat-card flask">
                <div class="stat-service">Flask (Secuencial)</div>
                <div class="stat-value">{flask_avg_rps:.1f}</div>
                <div class="stat-label">RPS Promedio</div>
            </div>
            <div class="stat-card">
                <div class="stat-service">Ray Serve (Paralelo)</div>
                <div class="stat-value">{ray_avg_latency:.1f}ms</div>
                <div class="stat-label">Latencia Promedio</div>
            </div>
            <div class="stat-card flask">
                <div class="stat-service">Flask (Secuencial)</div>
                <div class="stat-value">{flask_avg_latency:.1f}ms</div>
                <div class="stat-label">Latencia Promedio</div>
            </div>
        </div>
        
        <div class="comparison-highlight">
            <h3>🏆 Resultados Clave</h3>
"""
        
        if ray_avg_rps > flask_avg_rps:
            improvement = ((ray_avg_rps - flask_avg_rps) / flask_avg_rps * 100)
            html_content += f"<p><span class='winner'>Ray Serve</span> supera a Flask en throughput por <strong>{improvement:.1f}%</strong></p>"
        else:
            improvement = ((flask_avg_rps - ray_avg_rps) / ray_avg_rps * 100)
            html_content += f"<p><span class='winner'>Flask</span> supera a Ray Serve en throughput por <strong>{improvement:.1f}%</strong></p>"
        
        if ray_avg_latency < flask_avg_latency:
            improvement = ((flask_avg_latency - ray_avg_latency) / flask_avg_latency * 100)
            html_content += f"<p><span class='winner'>Ray Serve</span> tiene menor latencia por <strong>{improvement:.1f}%</strong></p>"
        else:
            improvement = ((ray_avg_latency - flask_avg_latency) / ray_avg_latency * 100)
            html_content += f"<p><span class='winner'>Flask</span> tiene menor latencia por <strong>{improvement:.1f}%</strong></p>"
        
        html_content += """
        </div>
        
        <div class="charts-section">
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">📈 Comparación de Throughput</div>
                    <img src="throughput_comparison.png" alt="Comparación de Throughput">
                </div>
                <div class="chart-container">
                    <div class="chart-title">⏱️ Análisis de Latencia</div>
                    <img src="latency_comparison.png" alt="Análisis de Latencia">
                </div>
                <div class="chart-container">
                    <div class="chart-title">📊 Escalabilidad</div>
                    <img src="concurrency_scaling.png" alt="Escalabilidad">
                </div>
                <div class="chart-container">
                    <div class="chart-title">🎯 Rendimiento por Endpoint</div>
                    <img src="endpoint_performance.png" alt="Rendimiento por Endpoint">
                </div>
                <div class="chart-container">
                    <div class="chart-title">💻 Recursos del Sistema</div>
                    <img src="system_resources.png" alt="Recursos del Sistema">
                </div>
                <div class="chart-container">
                    <div class="chart-title">❌ Análisis de Errores</div>
                    <img src="error_rates.png" alt="Análisis de Errores">
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Dashboard generado automáticamente por BenchmarkVisualizer</p>
            <p>Datos basados en {len(self.results)} pruebas de rendimiento</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Guardar dashboard
        with open(output_dir / 'dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("🌐 Dashboard interactivo generado: dashboard.html")


def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Generador de visualizaciones para benchmarks de Ray Serve vs Flask"
    )
    parser.add_argument(
        'results_file', 
        help='Archivo JSON con los resultados del benchmark'
    )
    parser.add_argument(
        '--output-dir', 
        default='benchmark_plots',
        help='Directorio de salida para los gráficos (default: benchmark_plots)'
    )
    parser.add_argument(
        '--format', 
        choices=['png', 'pdf', 'svg'], 
        default='png',
        help='Formato de los gráficos (default: png)'
    )
    parser.add_argument(
        '--style', 
        choices=['seaborn-v0_8', 'ggplot', 'bmh', 'classic'], 
        default='seaborn-v0_8',
        help='Estilo de los gráficos (default: seaborn-v0_8)'
    )
    parser.add_argument(
        '--no-dashboard', 
        action='store_true',
        help='No generar dashboard HTML interactivo'
    )
    parser.add_argument(
        '--no-report', 
        action='store_true',
        help='No generar reporte markdown'
    )
    
    args = parser.parse_args()
    
    # Verificar que el archivo existe
    if not Path(args.results_file).exists():
        print(f"❌ Error: No se encontró el archivo {args.results_file}")
        return 1
    
    try:
        # Crear visualizador
        visualizer = BenchmarkVisualizer(args.results_file)
        
        # Aplicar configuraciones
        if args.style != 'seaborn-v0_8':
            plt.style.use(args.style)
        
        # Crear directorio de salida
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"🎨 Generando visualizaciones en {output_dir}...")
        
        # Generar gráficos
        visualizer.create_comparison_plots()
        
        # Generar reporte si se solicita
        if not args.no_report:
            visualizer.generate_summary_report(output_dir)
        
        # Generar dashboard si se solicita
        if not args.no_dashboard:
            visualizer.create_interactive_dashboard(output_dir)
        
        print(f"""
✅ ¡Visualizaciones generadas exitosamente!

📁 Archivos creados en {output_dir}:
   📊 throughput_comparison.{args.format}
   ⏱️  latency_comparison.{args.format}
   📈 concurrency_scaling.{args.format}
   🎯 endpoint_performance.{args.format}
   💻 system_resources.{args.format}
   ❌ error_rates.{args.format}
   {'📄 benchmark_report.md' if not args.no_report else ''}
   {'🌐 dashboard.html' if not args.no_dashboard else ''}

🚀 Para ver el dashboard: abrir {output_dir}/dashboard.html en tu navegador
        """)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error durante la generación: {e}")
        return 1


if __name__ == "__main__":
    exit(main())