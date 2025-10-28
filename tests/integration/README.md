# Integration Testing Suite

This directory contains integration tests that run against the **real text-to-video server**, not mocked services.

## Prerequisites

Before running these tests, you **MUST** have the following services running:

1. **Text-to-Video Server** - Main application server
   ```bash
   cd /home/neil/Documents/text-to-video/server
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **TTS Service** (Chatterbox TTS API)
   ```bash
   cd /home/neil/Documents/text-to-video/chatterbox-tts-api
   python start.py
   ```

3. **LLM Service** (Ollama or OpenAI-compatible endpoint)
   ```bash
   # If using Ollama:
   ollama serve
   # Make sure qwen3:4b model is available:
   ollama pull qwen3:4b
   ```

4. **Redis** (for job tracking)
   ```bash
   redis-server
   ```

5. **Presenton Service** (Optional - for visual generation)
   ```bash
   # If you have Presenton running on port 9000
   ```

## Environment Setup

Copy the `.env.example` from the server directory and configure it:

```bash
cd /home/neil/Documents/text-to-video/server
cp .env.template .env
# Edit .env with your actual API keys and service URLs
```

## Running Integration Tests

### Run All Integration Tests
```bash
cd /home/neil/Documents/text-to-video/tests/integration
python run_integration_tests.py
```

### Run Individual Test Suites
```bash
# Performance tests
pytest test_integration_performance.py -v -s

# Reliability tests
pytest test_integration_reliability.py -v -s

# Resource usage tests
pytest test_integration_resources.py -v -s
```

### Run Specific Test
```bash
pytest test_integration_performance.py::test_single_request_performance -v -s
```

## Test Categories

### 1. Performance Tests (`test_integration_performance.py`)
- **Single Request Response Time**: Measure end-to-end response time
- **Concurrent Requests**: Test 1, 3, 5, 10 concurrent video generation requests
- **API Endpoint Latency**: Test health check, job status endpoints
- **Component Timing**: Measure individual service response times (LLM, TTS, Visual)

### 2. Reliability Tests (`test_integration_reliability.py`)
- **Normal Operation Success Rate**: Baseline success rate with real services
- **Service Failure Handling**: Test behavior when TTS/LLM services are down
- **Error Recovery**: Verify retry mechanisms and fallback behaviors
- **Data Integrity**: Verify generated assets and video outputs
- **Long-running Jobs**: Test stability over extended periods

### 3. Resource Usage Tests (`test_integration_resources.py`)
- **Memory Profiling**: Track memory usage during video generation
- **CPU Utilization**: Monitor CPU usage patterns
- **Disk I/O**: Measure file operations and storage usage
- **Network Bandwidth**: Track API request/response sizes
- **Cache Effectiveness**: Measure Redis cache hit rates
- **Concurrent Load**: Resource usage under multiple simultaneous jobs

## Test Configuration

Configure test parameters in each test file:

```python
# Server endpoints
BASE_URL = "http://localhost:8000"
TTS_URL = "http://localhost:4123"
LLM_URL = "http://localhost:11434"

# Test parameters
MAX_CONCURRENT_JOBS = 10
TEST_TIMEOUT = 300  # 5 minutes per test
```

## Generated Reports

Integration test reports are saved to `tests/integration/reports/`:

- `integration_performance_report.md` - Performance metrics
- `integration_reliability_report.md` - Reliability analysis
- `integration_resources_report.md` - Resource usage analysis

## Troubleshooting

### Tests Failing with Connection Errors
- Verify all required services are running
- Check that ports are not blocked by firewall
- Ensure server is accessible at `http://localhost:8000`

### Tests Timeout
- Increase `TEST_TIMEOUT` value in test files
- Check if services are responding slowly
- Monitor system resources (CPU, memory)

### Missing Dependencies
```bash
pip install -r ../requirements-tests.txt
```

### Redis Connection Errors
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

## Notes

- Integration tests are **slower** than unit tests (2-5 minutes per test)
- Tests use **real PDF document** (`2507.08034v1.pdf`)
- Tests create **actual files** in the server's output directories
- Clean up test files periodically to save disk space
- Tests may **consume API credits** if using paid LLM services
- Concurrent tests respect server's `MAX_CONCURRENT_JOBS` limit

## Comparison: Integration vs Unit Tests

| Aspect | Unit Tests (with Mocks) | Integration Tests (Real Server) |
|--------|-------------------------|----------------------------------|
| Speed | Fast (seconds) | Slow (minutes) |
| Dependencies | None | All services must run |
| Reliability | Always pass if code correct | Can fail due to external issues |
| Cost | Free | May consume API credits |
| Real-world accuracy | Low | High |
| Debugging value | Shows code issues | Shows system issues |

**Recommendation**: Run unit tests during development, integration tests before deployment.
