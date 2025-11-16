FROM python:3.10-slim

# Ensure Python prints straight to logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Expose the expected Cloud Run port
EXPOSE 8080

# Start Uvicorn (Cloud Run provides PORT env var)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
