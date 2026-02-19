FROM python:3.9-slim AS base

# Install system dependencies required by graphviz and other packages
RUN apt-get -qy update && apt-get -qy install --no-install-recommends \
    graphviz \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

# Install Python dependencies first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY fairos_api.py .
COPY code/ ./code/

# API port
EXPOSE 8000

CMD ["uvicorn", "fairos_api:app", "--host", "0.0.0.0", "--port", "8000"]
