#!/usr/bin/env python3
"""
High Volume Configuration Calculator
Helps determine optimal settings for handling high conversion volumes
"""
import psutil
import os

def analyze_system():
    """Analyze current system capabilities"""
    cpu_cores = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    print("🖥️  System Analysis:")
    print(f"   CPU Cores: {cpu_cores}")
    print(f"   Total RAM: {memory_gb:.1f} GB")
    print(f"   Available RAM: {psutil.virtual_memory().available / (1024**3):.1f} GB")
    
    return cpu_cores, memory_gb

def calculate_worker_recommendations(target_conversions_per_minute, avg_conversion_time=25):
    """Calculate optimal worker configuration"""
    
    # Basic calculation: workers needed = (target_per_minute * avg_time_seconds) / 60
    workers_needed = (target_conversions_per_minute * avg_conversion_time) / 60
    
    # Round up and add buffer
    recommended_workers = int(workers_needed * 1.2)  # 20% buffer
    
    return recommended_workers

def generate_configurations():
    """Generate configurations for different volume targets"""
    
    cpu_cores, memory_gb = analyze_system()
    
    print("\n📊 High Volume Configuration Recommendations:")
    print("=" * 60)
    
    scenarios = [
        {"name": "Medium Volume", "target": 20, "avg_time": 30},
        {"name": "High Volume", "target": 40, "avg_time": 25},
        {"name": "Very High Volume", "target": 60, "avg_time": 20},
        {"name": "Extreme Volume", "target": 100, "avg_time": 15}
    ]
    
    for scenario in scenarios:
        target = scenario["target"]
        avg_time = scenario["avg_time"]
        workers = calculate_worker_recommendations(target, avg_time)
        
        # System requirements
        min_cpu_cores = max(8, workers // 2)
        min_memory_gb = max(16, workers * 1.5)
        
        # Check if current system can handle it
        cpu_ok = cpu_cores >= min_cpu_cores
        memory_ok = memory_gb >= min_memory_gb
        
        print(f"\n🎯 {scenario['name']} ({target} conversions/minute):")
        print(f"   Recommended Workers: {workers}")
        print(f"   Timeout: {avg_time}s")
        print(f"   Min CPU Cores: {min_cpu_cores} {'✅' if cpu_ok else '❌'}")
        print(f"   Min RAM: {min_memory_gb}GB {'✅' if memory_ok else '❌'}")
        
        if cpu_ok and memory_ok:
            print(f"   Status: ✅ System can handle this volume")
            print(f"   Config: MAX_WORKERS={workers} CONVERSION_TIMEOUT={avg_time}")
        else:
            print(f"   Status: ❌ System upgrade needed")
            if not cpu_ok:
                print(f"   Need: {min_cpu_cores - cpu_cores} more CPU cores")
            if not memory_ok:
                print(f"   Need: {min_memory_gb - memory_gb:.1f}GB more RAM")

def generate_deployment_commands():
    """Generate deployment commands for different scenarios"""
    
    print(f"\n🚀 Deployment Commands:")
    print("=" * 40)
    
    configs = [
        {"workers": 8, "timeout": 30, "desc": "20 conversions/min"},
        {"workers": 12, "timeout": 25, "desc": "30 conversions/min"},
        {"workers": 16, "timeout": 20, "desc": "45 conversions/min"},
        {"workers": 20, "timeout": 18, "desc": "60 conversions/min"}
    ]
    
    for config in configs:
        workers = config["workers"]
        timeout = config["timeout"]
        desc = config["desc"]
        
        print(f"\n📋 For {desc}:")
        print(f"   # Environment variables")
        print(f"   export MAX_WORKERS={workers}")
        print(f"   export CONVERSION_TIMEOUT={timeout}")
        print(f"   python app.py")
        print(f"   ")
        print(f"   # Docker")
        print(f"   MAX_WORKERS={workers} CONVERSION_TIMEOUT={timeout} docker-compose up -d")

def check_libreoffice_limits():
    """Check LibreOffice concurrent instance limits"""
    
    print(f"\n⚠️  LibreOffice Limitations:")
    print("=" * 40)
    print("   - Max stable concurrent instances: ~15-20")
    print("   - Above 20 instances: potential instability")
    print("   - For >20 workers: consider multiple service instances")
    print("   - Use load balancer to distribute across instances")
    
    print(f"\n🏗️  Scaling Architecture for >60 conversions/minute:")
    print("   Option 1: Multiple service instances")
    print("     - Run 2-3 instances with 15 workers each")
    print("     - Use nginx/haproxy load balancer")
    print("     - Total capacity: 45-90 conversions/minute")
    print("   ")
    print("   Option 2: Hybrid approach")
    print("     - Primary: LibreOffice (15 workers)")
    print("     - Secondary: MS Word instances (10 workers)")
    print("     - Total capacity: 50-75 conversions/minute")

def monitoring_recommendations():
    """Provide monitoring recommendations for high volume"""
    
    print(f"\n📈 High Volume Monitoring:")
    print("=" * 40)
    print("   Essential metrics to monitor:")
    print("   - Worker utilization (keep < 90%)")
    print("   - Queue size (alert if > 50)")
    print("   - CPU usage (keep < 85%)")
    print("   - Memory usage (keep < 80%)")
    print("   - Conversion success rate (> 95%)")
    print("   - Average response time (< 30s)")
    print("   ")
    print("   Monitoring commands:")
    print("   watch -n 5 'curl -s http://localhost:8000/health | jq .performance_metrics'")
    print("   watch -n 2 'curl -s http://localhost:8000/queue/status | jq .queue_size'")

def main():
    """Main function"""
    print("🔧 PDF Converter High Volume Configuration Tool")
    print("=" * 60)
    
    generate_configurations()
    generate_deployment_commands()
    check_libreoffice_limits()
    monitoring_recommendations()
    
    print(f"\n💡 Key Recommendations:")
    print("   1. Start with conservative settings and scale up")
    print("   2. Monitor system resources continuously")
    print("   3. Use SSD storage for temp files")
    print("   4. Consider multiple instances for >60/min")
    print("   5. Implement proper load balancing")
    print("   6. Set up alerting for queue size and failures")

if __name__ == "__main__":
    main()
