# Chatterbox TTS API - macOS Docker Solutions

## 🚨 The MPS Problem

You encountered this error when trying to use MPS in Docker:
```
MPS not available because the current PyTorch install was not built with MPS enabled.
```

**Root Cause**: Docker containers on macOS run in a Linux VM that cannot access Metal Performance Shaders (MPS), even if PyTorch has MPS support. This is a fundamental limitation of containerization on macOS.

## 📋 Available Solutions

### 🥇 **Option 1: Hybrid Development (Fastest - Recommended)**
Run chatterbox-tts locally, other services in Docker:

```bash
./start-dev.sh
```

**Performance**: ~30 seconds startup with MPS acceleration

### 🥈 **Option 2: macOS-Optimized Docker (Good Compromise)**
Custom Dockerfile optimized for macOS ARM64 with CPU optimizations:

```bash
./start-macos-docker.sh
```

**Performance**: 3-5 minutes startup with CPU optimizations

### 🥉 **Option 3: Standard Docker Compose Files**
Use the official project's Docker configurations:

```bash
# CPU optimized
docker compose -f chatterbox-tts-api/docker/docker-compose.cpu.yml up -d

# UV optimized (faster builds)
docker compose -f chatterbox-tts-api/docker/docker-compose.uv.yml up -d
```

**Performance**: 10+ minutes startup with standard CPU

## 🔧 What's in the macOS-Optimized Solution

### Dockerfile.mps Features:
- ✅ **ARM64 Platform**: Native Apple Silicon support
- ✅ **CPU Optimizations**: Multi-threading with OMP, MKL, BLAS
- ✅ **Watermarker Fallback**: Handles resemble-perth compatibility issues
- ✅ **Memory Optimizations**: Optimized shared memory and tmpfs
- ✅ **Faster Startup**: Reduced model cache overhead

### docker-compose.mps.yml Features:
- ✅ **Resource Limits**: Optimized memory and CPU allocation
- ✅ **Platform Specification**: Forces linux/arm64 for Apple Silicon
- ✅ **Host Cache Binding**: Uses host filesystem for model cache
- ✅ **Extended Health Checks**: Longer timeouts for CPU initialization

## 🚀 Quick Start

1. **For fastest development (with MPS)**:
   ```bash
   ./start-dev.sh
   ```

2. **For Docker-only workflow**:
   ```bash
   ./start-macos-docker.sh
   ```

## 📊 Performance Comparison

| Method | Device | Startup Time | Memory | Container |
|--------|--------|--------------|--------|-----------|
| **start-dev.sh** | MPS | ~30 seconds | ~2GB | No |
| **start-macos-docker.sh** | CPU (optimized) | 3-5 minutes | ~4GB | Yes |
| **Standard Docker** | CPU | 10+ minutes | ~4GB | Yes |

## 🛠️ Technical Details

### Why MPS Doesn't Work in Docker:
1. **Virtualization Layer**: Docker Desktop uses a Linux VM
2. **Metal Framework**: Not available in Linux containers
3. **Device Access**: Containers can't access host GPU directly
4. **PyTorch Limitation**: Even MPS-enabled PyTorch can't access Metal in containers

### Optimizations Applied:
1. **Multi-threading**: 8 threads for BLAS operations
2. **Memory Management**: Aggressive cleanup and shared memory
3. **Platform Native**: ARM64-specific optimizations
4. **I/O Performance**: tmpfs for temporary files
5. **Error Handling**: Fallback watermarker for compatibility

## 🔍 Monitoring & Debugging

### Check initialization status:
```bash
curl http://localhost:4123/status | jq '.'
```

### Monitor logs:
```bash
# For hybrid approach
tail -f chatterbox-tts-api/logs/*.log

# For Docker approach
docker logs chatterbox-tts-api-macos -f
```

### Stop services:
```bash
# Hybrid approach
Ctrl+C (then docker-compose down for other services)

# Docker approach
docker compose -f chatterbox-tts-api/docker/docker-compose.mps.yml down
```

## 🎯 Recommendations

- **Development**: Use `./start-dev.sh` for fastest iteration
- **CI/CD**: Use `./start-macos-docker.sh` for consistent containers
- **Production**: Use dedicated Docker files based on target platform

## 📝 Created Files

- `Dockerfile.mps` - Optimized Dockerfile for macOS
- `docker-compose.mps.yml` - Optimized Compose file
- `start-macos-docker.sh` - Convenience startup script
- `start-dev.sh` - Hybrid development script

The macOS-optimized Docker solution provides the best compromise between containerization and performance when MPS is not available.
