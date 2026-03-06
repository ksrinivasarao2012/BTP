FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for pygame (headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set pygame to run headless (no display needed in container)
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy

# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install CPU-only PyTorch first (much smaller ~200MB vs ~900MB full)
RUN pip install --no-cache-dir --timeout 600 \
    torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir --timeout 600 -r requirements.txt

# Copy the entire project
COPY . .

# Default command: run the 1K test suite
CMD ["python", "test_suite_step_A.py", "1k"]
