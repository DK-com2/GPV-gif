# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for cartopy and netCDF4
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    libproj-dev \
    libhdf5-dev \
    libnetcdf-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY scripts/ scripts/
COPY config/ config/
COPY templates/ templates/

# Create necessary directories
RUN mkdir -p data/raw data/logs output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo

# Expose port for Flask app
EXPOSE 5000

# Run the Flask application with scheduler
CMD ["python", "app.py"]
