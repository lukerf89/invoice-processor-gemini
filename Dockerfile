FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements.dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements.dev.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY test_scripts/ ./test_scripts/

# Create necessary directories
RUN mkdir -p debug_output test_invoices

# Set Python path
ENV PYTHONPATH=/app/src

# Set default environment
ENV ENVIRONMENT=development
ENV FUNCTIONS_FRAMEWORK_DEBUG=true

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Default command
CMD ["functions-framework", "--target=process_invoice", "--port=8080", "--host=0.0.0.0", "--source=src/main_updated.py"]