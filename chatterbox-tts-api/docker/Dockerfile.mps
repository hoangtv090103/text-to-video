# Optimized Dockerfile for macOS Docker (ARM64 with CPU optimizations)
# This provides the best possible performance when MPS is not available
FROM --platform=linux/arm64 python:3.11-slim

# Set environment variables for optimal CPU performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# CPU optimization environment variables
ENV OMP_NUM_THREADS=8
ENV MKL_NUM_THREADS=8
ENV TORCH_NUM_THREADS=8
ENV OPENBLAS_NUM_THREADS=8
ENV VECLIB_MAXIMUM_THREADS=8

# Install system dependencies optimized for ARM64
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    ffmpeg \
    libsndfile1 \
    libblas-dev \
    liblapack-dev \
    libopenblas-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Create virtual environment
RUN uv venv --python 3.11

# Install optimized PyTorch for ARM64 CPU
# Use the CPU-optimized version with MKL support
RUN uv pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu

# Install base dependencies
RUN uv pip install fastapi uvicorn[standard] python-dotenv python-multipart requests psutil

# Install numpy with optimized BLAS
RUN uv pip install numpy

# Pre-install build dependencies for problematic packages
RUN uv pip install wheel setuptools cython

# Install resemble-perth with error handling
RUN uv pip install resemble-perth || echo "Warning: resemble-perth installation failed, continuing..."

# Create a fallback for the watermarker if needed
COPY <<EOF /app/watermarker_fallback.py
import sys
import warnings

def patch_watermarker():
    try:
        import perth
        # Check if PerthImplicitWatermarker is available and callable
        if not hasattr(perth, 'PerthImplicitWatermarker') or perth.PerthImplicitWatermarker is None:
            print("⚠️  PerthImplicitWatermarker not available, creating fallback")

            class FallbackWatermarker:
                def __init__(self):
                    warnings.warn("Using fallback watermarker - no watermarking will be applied", UserWarning)

                def __call__(self, audio, *args, **kwargs):
                    return audio

                def watermark(self, audio, *args, **kwargs):
                    return audio

            perth.PerthImplicitWatermarker = FallbackWatermarker
            print("✓ Fallback watermarker configured")
        else:
            print("✓ PerthImplicitWatermarker is available")
    except ImportError as e:
        print(f"⚠️  perth module not available: {e}")
        # Create a mock perth module
        import types
        perth = types.ModuleType('perth')

        class FallbackWatermarker:
            def __init__(self):
                warnings.warn("Using mock watermarker - no watermarking will be applied", UserWarning)

            def __call__(self, audio, *args, **kwargs):
                return audio

            def watermark(self, audio, *args, **kwargs):
                return audio

        perth.PerthImplicitWatermarker = FallbackWatermarker
        sys.modules['perth'] = perth
        print("✓ Mock watermarker module created")

if __name__ == "__main__":
    patch_watermarker()
EOF

# Apply the watermarker patch before installing chatterbox-tts
RUN python /app/watermarker_fallback.py

# Install chatterbox-tts with proper build isolation handling
RUN uv pip install --no-build-isolation "chatterbox-tts @ git+https://github.com/resemble-ai/chatterbox.git" || \
    (echo "Direct install failed, trying with build isolation..." && \
     uv pip install "chatterbox-tts @ git+https://github.com/resemble-ai/chatterbox.git") || \
    (echo "Git install failed, trying PyPI..." && \
     uv pip install --no-build-isolation chatterbox-tts) || \
    (echo "All install methods failed, trying manual dependency resolution..." && \
     uv pip install pkuseg --no-build-isolation && \
     uv pip install chatterbox-tts)

# Copy application code
COPY app/ ./app/
COPY main.py ./

# Create a patched main.py that applies the watermarker fix
RUN cp main.py main.py.original && \
    echo "import sys; sys.path.insert(0, '/app')" > main.py.new && \
    echo "import watermarker_fallback; watermarker_fallback.patch_watermarker()" >> main.py.new && \
    cat main.py.original >> main.py.new && \
    mv main.py.new main.py

# Copy voice sample
COPY voice-sample.mp3 ./voice-sample.mp3

# Create directories for model cache and voice library
RUN mkdir -p /cache /voices

# Set environment variables optimized for CPU performance
ENV PORT=4123
ENV EXAGGERATION=0.5
ENV CFG_WEIGHT=0.5
ENV TEMPERATURE=0.8
ENV VOICE_SAMPLE_PATH=/app/voice-sample.mp3
ENV MAX_CHUNK_LENGTH=280
ENV MAX_TOTAL_LENGTH=3000
ENV DEVICE=cpu
ENV MODEL_CACHE_DIR=/cache
ENV VOICE_LIBRARY_DIR=/voices
ENV HOST=0.0.0.0

# PyTorch optimizations for CPU
ENV TORCH_CUDNN_V8_API_ENABLED=1
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Add uv venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10m --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use a startup script that optimizes CPU performance
COPY <<EOF /app/start.sh
#!/bin/bash
echo "🚀 Starting Chatterbox TTS API (CPU Optimized for ARM64)"
echo "================================================================"
echo "CPU Cores: \$(nproc)"
echo "Memory: \$(free -h | grep '^Mem:' | awk '{print \$2}')"
echo "PyTorch Threads: \$TORCH_NUM_THREADS"
echo "================================================================"

# Set CPU governor to performance if possible (may not work in container)
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true

# Start the application
exec python main.py
EOF

RUN chmod +x /app/start.sh

# Use the optimized start script
CMD ["/app/start.sh"]
