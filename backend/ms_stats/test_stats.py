import requests
import json
import time

def print_json_pretty(data, title):
    """Imprime JSON de forma legible."""
    print(f"\n{'='*15} {title} {'='*15}")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def test_docker_services():
    """Prueba los servicios ms_loader y ms_stats en Docker."""
    print("🐳 PROBANDO MICROSERVICIOS EN DOCKER")
    print("=" * 50)
    
    # URLs de los servicios
    loader_url = "http://localhost:8000"
    stats_url = "http://localhost:8001"
    
    # 1. Verificar ms_loader
    print("\n📊 VERIFICANDO MS_LOADER")
    print("-" * 30)
    try:
        response = requests.get(f"{loader_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ ms_loader está disponible")
            print_json_pretty(response.json(), "MS_LOADER HEALTH")
        else:
            print(f"⚠️  ms_loader responde con error: {response.status_code}")
    except Exception as e:
        print(f"❌ ms_loader no disponible: {e}")
        return False
    
    # 2. Verificar ms_stats
    print("\n📈 VERIFICANDO MS_STATS")
    print("-" * 30)
    try:
        response = requests.get(f"{stats_url}/", timeout=15)
        if response.status_code == 200:
            print("✅ ms_stats está disponible")
            print_json_pretty(response.json(), "MS_STATS STATUS")
        else:
            print(f"⚠️  ms_stats responde con error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ms_stats no disponible: {e}")
        print("Posibles causas:")
        print("- El contenedor no está corriendo")
        print("- Ray Serve está iniciando (puede tardar)")
        print("- Error en la configuración")
        return False
    
    # 3. Probar endpoints de estadísticas
    print("\n🔍 PROBANDO ENDPOINTS DE ESTADÍSTICAS")
    print("-" * 40)
    
    endpoints = [
        ("/stats/basic", "ESTADÍSTICAS BÁSICAS"),
        ("/stats/summary", "RESUMEN DE DATOS"),
        ("/stats/prices", "ESTADÍSTICAS DE PRECIOS"),
        ("/stats/by_ticker/AAPL", "ESTADÍSTICAS PARA AAPL")
    ]
    
    successful_tests = 0
    
    for endpoint, title in endpoints:
        try:
            print(f"\n🔄 Probando: {stats_url}{endpoint}")
            response = requests.get(f"{stats_url}{endpoint}", timeout=30)
            
            if response.status_code == 200:
                print(f"✅ {title} - Status: {response.status_code}")
                data = response.json()
                
                # Mostrar resumen de la respuesta
                if "statistics" in data:
                    print(f"   📊 Estadísticas calculadas para {len(data.get('statistics', {}))} métricas")
                if "total_records" in data:
                    print(f"   📝 Total de registros: {data['total_records']}")
                if "service" in data:
                    print(f"   🔧 Servicio: {data['service']}")
                
                successful_tests += 1
                
            else:
                print(f"⚠️  {title} - Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   Error text: {response.text[:100]}...")
            
            time.sleep(1)  # Pausa entre requests
            
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout para {endpoint} - Ray puede estar procesando")
        except Exception as e:
            print(f"❌ Error en {endpoint}: {e}")
    
    # 4. Resumen final
    print(f"\n📊 RESUMEN FINAL")
    print("=" * 20)
    print(f"✅ Tests exitosos: {successful_tests}/{len(endpoints)}")
    print(f"❌ Tests fallidos: {len(endpoints) - successful_tests}/{len(endpoints)}")
    
    if successful_tests > 0:
        print("\n🎉 ¡Servicios funcionando!")
        print("\n📚 ENDPOINTS DISPONIBLES:")
        print(f"• Estado ms_loader: {loader_url}/health")
        print(f"• Estado ms_stats: {stats_url}/")
        print(f"• Estadísticas básicas: {stats_url}/stats/basic")
        print(f"• Resumen: {stats_url}/stats/summary")
        print(f"• Precios: {stats_url}/stats/prices")
        print(f"• Por ticker: {stats_url}/stats/by_ticker/AAPL")
        print(f"• Recargar: {stats_url}/stats/reload")
    else:
        print("\n❌ Hay problemas con los servicios")
        print("Revisa los logs con: docker-compose logs ms_stats")
    
    return successful_tests > 0

def check_docker_status():
    """Verifica el estado de los contenedores Docker."""
    print("🐳 VERIFICANDO CONTENEDORES DOCKER")
    print("=" * 35)
    print("Ejecuta estos comandos para verificar:")
    print("• docker-compose ps")
    print("• docker-compose logs ms_loader")
    print("• docker-compose logs ms_stats")
    print()

if __name__ == "__main__":
    check_docker_status()
    
    print("⏳ Esperando 3 segundos para que los servicios estén listos...")
    time.sleep(3)
    
    success = test_docker_services()
    
    if not success:
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Verifica que los contenedores estén corriendo:")
        print("   docker-compose ps")
        print("2. Revisa los logs:")
        print("   docker-compose logs ms_stats")
        print("3. Reinicia los servicios:")
        print("   docker-compose down && docker-compose up --build")