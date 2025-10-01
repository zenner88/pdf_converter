#!/bin/bash
# Setup Nginx reverse proxy for PDF Converter

echo "🔧 Setting up Nginx reverse proxy for PDF Converter"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo ./setup_nginx.sh"
    exit 1
fi

# Install nginx if not installed
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing Nginx..."
    apt-get update
    apt-get install -y nginx
fi

# Backup existing nginx config
if [ -f /etc/nginx/sites-available/default ]; then
    cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
    echo "✅ Backed up existing nginx config"
fi

# Copy our nginx config
cp nginx.conf /etc/nginx/sites-available/pdf-converter

# Create symlink to enable site
ln -sf /etc/nginx/sites-available/pdf-converter /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration is valid"
    
    # Restart nginx
    systemctl restart nginx
    systemctl enable nginx
    
    echo "🎉 Nginx setup completed!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Update nginx.conf with your domain name"
    echo "2. Start PDF Converter: python3 app.py"
    echo "3. Access without port: http://your-domain.com"
    echo ""
    echo "🔍 Check status:"
    echo "   systemctl status nginx"
    echo "   curl http://localhost/health"
    
else
    echo "❌ Nginx configuration error"
    exit 1
fi
