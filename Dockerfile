# Multi-stage build for optimized Docker image
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (layer caching)
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

LABEL maintainer="Agent 2 - Consistency Analyzer"
LABEL version="1.0.0"
LABEL description="DDD Domain Model Validation Agent with A2A Protocol"

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY app/ ./app/
COPY a2a/ ./a2a/
COPY knowledge_base/ ./knowledge_base/
COPY input_agent/ ./input_agent/

# Create necessary directories
RUN mkdir -p /app/output_agent /app/logs && \
    chmod -R 755 /app

# Create non-root user for security
RUN useradd -m -u 1000 agent2user && \
    chown -R agent2user:agent2user /app

# Switch to non-root user
USER agent2user

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Default command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
