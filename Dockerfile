# Build stage: install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage: create minimal image
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --uid 1000 botuser && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Make sure Python can find user-installed packages
ENV PATH=/root/.local/bin:$PATH

# Expose health check port
EXPOSE 8080

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the bot
CMD ["python", "-m", "src.main"]
