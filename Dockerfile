FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install Node.js dependencies if package.json exists
RUN if [ -f package.json ]; then npm install; fi

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "scripts.pipeline"]
