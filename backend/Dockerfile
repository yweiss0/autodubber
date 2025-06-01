FROM python:3.11-slim

# Install system dependencies including FFmpeg and curl
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick policy to allow MoviePy operations
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="PS"/rights="read|write" pattern="PS"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="EPS"/rights="read|write" pattern="EPS"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="XPS"/rights="read|write" pattern="XPS"/' /etc/ImageMagick-6/policy.xml

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for media storage
RUN mkdir -p media/uploads media/outputs media/temp

# Disable Uvicorn autoreload inside the container to avoid frequent restarts
ENV DEV_RELOAD=0

# Expose port
EXPOSE 8000

# Set dummy ElevenLabs API key to prevent startup failure
ENV ELEVENLABS_API_KEY=dummy_key_will_be_replaced_at_runtime

# Run the application
CMD ["python", "run.py"] 