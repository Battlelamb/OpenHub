FROM node:22-slim AS dashboard-build

WORKDIR /dashboard

# Install dashboard dependencies first for Docker layer caching.
COPY web/package*.json ./
RUN npm ci

# Build the React dashboard bundle that FastAPI serves from /dashboard.
COPY web/ ./
RUN npm run build

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and migration config
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy the compiled React dashboard into the location app.main mounts.
COPY --from=dashboard-build /dashboard/dist ./web/dist

# Create data directories
RUN mkdir -p data/state data/artifacts

# Create non-root user for production safety
RUN groupadd -r openhub && useradd -r -g openhub -d /app -s /sbin/nologin openhub \
    && chown -R openhub:openhub /app

# Switch to non-root user
USER openhub

# Expose port
EXPOSE 7788

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:7788/v1/health || exit 1

# Production command (no --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7788"]
