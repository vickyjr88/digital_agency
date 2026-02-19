FROM python:3.9-slim

WORKDIR /app

# Install runtime dependencies only (psycopg2-binary needs libpq at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from current directory (backend_dexter context)
COPY . .

# Expose port
EXPOSE 8000

# Command
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
