FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
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
