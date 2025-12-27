FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Install system dependencies including Tesseract OCR and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt /code/requirements.txt

# Install Python dependencies including fastapi-cli
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi-cli

# Copy the backend directory
COPY backend /code/backend

# Expose port
EXPOSE 8000

# Start FastAPI using the fastapi command
CMD ["fastapi", "run", "backend/main.py", "--host", "0.0.0.0", "--port", "8000"]
