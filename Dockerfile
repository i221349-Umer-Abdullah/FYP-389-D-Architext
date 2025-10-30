# Architext Docker Image
# Production-ready containerized deployment

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p outputs models data logs \
    && chmod -R 755 outputs models data logs

# Set environment variables
ENV ARCHITEXT_ENV=production
ENV ARCHITEXT_HOST=0.0.0.0
ENV ARCHITEXT_PORT=7860
ENV ARCHITEXT_DEBUG=false
ENV ARCHITEXT_SHARE=false
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/', timeout=5)" || exit 1

# Run the application
CMD ["python", "app/demo_app.py"]
