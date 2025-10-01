#!/bin/bash
# Test script untuk menguji berbagai konfigurasi worker
# Hanya untuk testing dan monitoring - tidak mengubah service

echo "🧪 Multiple Worker Configuration Testing"
echo "========================================"
echo ""

# Default values
HOST="localhost"
PORT=8000
SERVICE_URL="http://$HOST:$PORT"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            SERVICE_URL="http://$HOST:$PORT"
            shift 2
            ;;
        --port)
            PORT="$2"
            SERVICE_URL="http://$HOST:$PORT"
            shift 2
            ;;
        --url)
            SERVICE_URL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST     Service host (default: localhost)"
            echo "  --port PORT     Service port (default: 8000)"
            echo "  --url URL       Full service URL"
            echo "  -h, --help      Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                              # Test localhost:8000"
            echo "  $0 --port 8080                 # Test localhost:8080"
            echo "  $0 --url http://server:8000    # Test remote server"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🎯 Testing service at: $SERVICE_URL"
echo ""

# Check if service is accessible
echo "🔍 Checking service availability..."
if ! curl -s --connect-timeout 5 "$SERVICE_URL/" > /dev/null; then
    echo "❌ Cannot connect to service at $SERVICE_URL"
    echo "   Make sure the service is running and accessible"
    exit 1
fi

echo "✅ Service is accessible"
echo ""

# Get current service info
echo "📊 Current Service Configuration:"
SERVICE_INFO=$(curl -s "$SERVICE_URL/" | python3 -m json.tool 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$SERVICE_INFO"
else
    echo "   Could not retrieve service info"
fi
echo ""

# Test scenarios
echo "🚀 Running Performance Tests..."
echo ""

# Light test
echo "1️⃣ Light Load Test (2 concurrent, 10 total)"
echo "   This simulates normal usage patterns"
python3 test_workers.py --url "$SERVICE_URL" --light
echo ""

# Check system resources after light test
echo "📈 System Resources After Light Test:"
HEALTH_INFO=$(curl -s "$SERVICE_URL/health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    resources = data.get('system_resources', {})
    recommendations = data.get('recommendations', {})
    print(f\"   CPU: {resources.get('cpu_percent', 'N/A')}%\")
    print(f\"   Memory: {resources.get('memory_percent', 'N/A')}%\")
    print(f\"   Worker Utilization: {data.get('worker_utilization', 'N/A')}\")
    print(f\"   Load Level: {recommendations.get('current_load', 'N/A')}\")
    print(f\"   Suggestion: {recommendations.get('suggested_action', 'N/A')}\")
except:
    print('   Could not retrieve health info')
")
echo "$HEALTH_INFO"
echo ""

# Wait between tests
echo "⏳ Waiting 15 seconds before next test..."
sleep 15

# Medium test
echo "2️⃣ Medium Load Test (5 concurrent, 20 total)"
echo "   This simulates moderate usage with multiple users"
python3 test_workers.py --url "$SERVICE_URL"
echo ""

# Final recommendations
echo "💡 FINAL RECOMMENDATIONS:"
echo "========================"

FINAL_HEALTH=$(curl -s "$SERVICE_URL/health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    resources = data.get('system_resources', {})
    recommendations = data.get('recommendations', {})
    max_workers = data.get('max_workers', 'N/A')
    cpu = resources.get('cpu_percent', 0)
    memory = resources.get('memory_percent', 0)
    cores = resources.get('cpu_cores', 'N/A')
    
    print(f\"Current Configuration:\")
    print(f\"   Max Workers: {max_workers}\")
    print(f\"   CPU Cores: {cores}\")
    print(f\"   Current CPU: {cpu}%\")
    print(f\"   Current Memory: {memory}%\")
    print(f\"\")
    
    if cpu < 60 and memory < 60:
        print(f\"✅ System has capacity for more workers\")
        if max_workers < 8:
            print(f\"   Consider increasing to 6-8 workers\")
        elif max_workers < 12:
            print(f\"   Consider increasing to 10-12 workers\")
        else:
            print(f\"   Current worker count seems optimal\")
    elif cpu > 80 or memory > 80:
        print(f\"⚠️  System is under stress\")
        print(f\"   Consider reducing workers or upgrading hardware\")
    else:
        print(f\"✅ Current configuration appears balanced\")
    
    print(f\"\")
    print(f\"Monitoring Commands:\")
    print(f\"   curl {sys.argv[1] if len(sys.argv) > 1 else '$SERVICE_URL'}/health\")
    print(f\"   watch -n 2 'curl -s {sys.argv[1] if len(sys.argv) > 1 else '$SERVICE_URL'}/ | jq .worker_utilization'\")
    
except Exception as e:
    print(f'Could not generate recommendations: {e}')
" "$SERVICE_URL")

echo "$FINAL_HEALTH"
echo ""
echo "🏁 Testing completed!"
echo ""
echo "📝 Notes:"
echo "   - This script only tests and monitors"
echo "   - It does NOT change your service configuration"
echo "   - To change workers: export MAX_WORKERS=15 && restart service"
echo "   - Monitor continuously during production load"
