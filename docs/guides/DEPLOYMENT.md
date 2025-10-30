# Architext Deployment Guide

Complete guide for deploying Architext in various environments.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Monitoring & Logging](#monitoring--logging)
6. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Python 3.8+ installed
- 8GB+ RAM (16GB recommended)
- Optional: NVIDIA GPU with CUDA support

### Quick Start

1. **Clone and setup:**
   ```bash
   cd architext
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

4. **Run the application:**
   ```bash
   python app/demo_app.py
   ```

5. **Access the UI:**
   - Local: http://localhost:7860
   - Public share link will be displayed if enabled

---

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Build and run:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f architext
   ```

3. **Stop the service:**
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t architext:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 7860:7860 \
     -v $(pwd)/outputs:/app/outputs \
     -v $(pwd)/models:/app/models \
     -v $(pwd)/logs:/app/logs \
     --name architext \
     architext:latest
   ```

3. **Access logs:**
   ```bash
   docker logs -f architext
   ```

---

## Production Deployment

### Prerequisites
- Linux server (Ubuntu 20.04+ recommended)
- 16GB+ RAM
- NVIDIA GPU (optional but recommended)
- Docker and Docker Compose installed
- Domain name configured (for HTTPS)

### Step-by-Step Production Setup

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Clone Repository

```bash
cd /opt
sudo git clone <your-repo-url> architext
cd architext
```

#### 3. Configure Environment

```bash
# Copy and edit environment file
sudo cp .env.example .env
sudo nano .env
```

**Production .env settings:**
```bash
ARCHITEXT_ENV=production
ARCHITEXT_HOST=0.0.0.0
ARCHITEXT_PORT=7860
ARCHITEXT_DEBUG=false
ARCHITEXT_SHARE=false
ARCHITEXT_LOG_LEVEL=WARNING
ARCHITEXT_RATE_LIMIT=true
ARCHITEXT_RATE_LIMIT_RPM=10
# Add authentication
ARCHITEXT_AUTH=admin:your_secure_password_here
```

#### 4. Set Up Reverse Proxy (Nginx)

Create `/etc/nginx/sites-available/architext`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (use certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to Gradio
    location / {
        proxy_pass http://localhost:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running generations
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Increase client body size for file uploads
    client_max_body_size 50M;
}
```

Enable and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/architext /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 5. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

#### 6. Deploy with Docker Compose

```bash
sudo docker-compose up -d
```

#### 7. Enable Automatic Startup

```bash
# Docker will restart containers automatically with:
# restart: unless-stopped
```

#### 8. Set Up Monitoring

Create systemd service for monitoring:

```bash
sudo nano /etc/systemd/system/architext-monitor.service
```

```ini
[Unit]
Description=Architext Monitoring
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker-compose -f /opt/architext/docker-compose.yml ps

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable architext-monitor.service
sudo systemctl start architext-monitor.service
```

---

## Environment Configuration

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ARCHITEXT_ENV` | development | Environment: development, staging, production |
| `ARCHITEXT_HOST` | 0.0.0.0 | Server host |
| `ARCHITEXT_PORT` | 7860 | Server port |
| `ARCHITEXT_DEBUG` | false | Enable debug mode |
| `ARCHITEXT_MODEL` | shap-e | Default AI model |
| `ARCHITEXT_QUALITY` | medium | Default generation quality |
| `ARCHITEXT_USE_GPU` | true | Use GPU if available |
| `ARCHITEXT_LOG_LEVEL` | INFO | Logging level |
| `ARCHITEXT_SHARE` | true | Enable Gradio share link |
| `ARCHITEXT_AUTH` | (none) | Authentication (username:password) |
| `ARCHITEXT_RATE_LIMIT` | false | Enable rate limiting |
| `ARCHITEXT_RATE_LIMIT_RPM` | 10 | Requests per minute limit |

### Configuration File

Edit `config.py` for advanced configuration:
- Model cache paths
- Output directories
- Performance tuning
- Feature flags

---

## Monitoring & Logging

### Log Files

Logs are stored in `logs/` directory:
- `architext_development.log` - Development logs
- `architext_production.log` - Production logs

### View Logs

**Docker:**
```bash
docker-compose logs -f architext
```

**Local:**
```bash
tail -f logs/architext_development.log
```

### Log Rotation

Logs automatically rotate at 10MB with 5 backups kept.

Configure in `config.py`:
```python
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

### Monitoring Metrics

**System Metrics:**
```bash
# CPU and memory usage
docker stats architext

# Disk usage
du -sh outputs/ models/ logs/
```

**Application Metrics:**
Check logs for generation metrics:
```bash
grep "Generation successful" logs/architext_production.log | wc -l
grep "Generation failed" logs/architext_production.log
```

---

## Troubleshooting

### Common Issues

#### 1. Out of Memory

**Symptoms:** Generation fails, container restarts

**Solutions:**
- Reduce quality to "Low"
- Disable GPU: `ARCHITEXT_USE_GPU=false`
- Increase Docker memory limit
- Use smaller batch sizes

#### 2. Slow Generation

**Symptoms:** Takes >5 minutes to generate

**Solutions:**
- Enable GPU if available
- Use "Low" or "Medium" quality
- Check system resources (CPU/RAM)
- Verify model cache is populated

#### 3. Port Already in Use

**Symptoms:** Cannot start server on port 7860

**Solutions:**
```bash
# Find process using port
netstat -ano | findstr :7860  # Windows
lsof -i :7860  # Linux/Mac

# Kill process or change port
ARCHITEXT_PORT=7861
```

#### 4. Model Download Fails

**Symptoms:** Error loading model, timeout

**Solutions:**
- Check internet connection
- Verify disk space (models are 2-3GB)
- Try manual download and place in `models/` directory
- Use different mirror/proxy

#### 5. Docker Build Fails

**Symptoms:** Build error during pip install

**Solutions:**
```bash
# Clear Docker cache
docker system prune -a

# Build with no cache
docker build --no-cache -t architext:latest .

# Check system resources
docker info
```

### Debug Mode

Enable debug mode for verbose logging:

```bash
export ARCHITEXT_DEBUG=true
export ARCHITEXT_LOG_LEVEL=DEBUG
python app/demo_app.py
```

### Health Check

**Docker:**
```bash
docker inspect --format='{{.State.Health.Status}}' architext
```

**Manual:**
```bash
curl http://localhost:7860/
```

### Getting Help

1. Check logs first
2. Review error messages carefully
3. Search existing issues on GitHub
4. Create new issue with:
   - Error message
   - Environment details
   - Steps to reproduce

---

## Performance Tuning

### GPU Optimization

```bash
# Check NVIDIA GPU
nvidia-smi

# Enable GPU in Docker
docker run --gpus all ...
```

### Memory Optimization

Edit `config.py`:
```python
MEMORY_LIMIT_GB = 8  # Adjust based on available RAM
MAX_BATCH_SIZE = 1    # Keep at 1 for demo
```

### Model Caching

Pre-download models:
```python
from transformers import pipeline

# This will cache models
pipeline("text-to-image", model="openai/shap-e")
```

---

## Backup & Recovery

### What to Backup

1. **Generated Models:** `outputs/`
2. **Configuration:** `.env`, `config.py`
3. **Logs:** `logs/` (optional)
4. **Model Cache:** `models/` (optional, can re-download)

### Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/backup/architext/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup outputs
tar -czf $BACKUP_DIR/outputs.tar.gz outputs/

# Backup config
cp .env $BACKUP_DIR/
cp config.py $BACKUP_DIR/

# Backup logs
tar -czf $BACKUP_DIR/logs.tar.gz logs/

echo "Backup complete: $BACKUP_DIR"
```

### Recovery

```bash
# Extract backups
tar -xzf outputs.tar.gz
tar -xzf logs.tar.gz

# Restore config
cp backup/.env .
```

---

## Security Considerations

### Authentication

Always enable authentication in production:
```bash
ARCHITEXT_AUTH=admin:strong_random_password_here
```

### HTTPS

Use HTTPS in production (Let's Encrypt):
```bash
sudo certbot --nginx -d your-domain.com
```

### Rate Limiting

Enable to prevent abuse:
```bash
ARCHITEXT_RATE_LIMIT=true
ARCHITEXT_RATE_LIMIT_RPM=10
```

### Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Scaling

### Horizontal Scaling

Use load balancer (e.g., Nginx) with multiple instances:

```nginx
upstream architext {
    server localhost:7860;
    server localhost:7861;
    server localhost:7862;
}
```

### Vertical Scaling

- Increase RAM
- Add GPU
- Use faster storage (SSD)

---

## Support

- **Documentation:** README.md, QUICK_START.md
- **Issues:** GitHub Issues
- **Email:** your-email@domain.com

---

**Last Updated:** 2024-10-30
**Version:** 1.0.0 (Iteration 1)
