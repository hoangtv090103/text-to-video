# Integration Tests - Quick Start Guide

## What Are Integration Tests?

Integration tests run against the **real, running server** with all actual services (LLM, TTS, Redis, etc.). Unlike unit tests that use mocks, these tests verify that your entire system works correctly in a real-world environment.

## Prerequisites Checklist

Before running integration tests, ensure all services are running:

- [ ] **Text-to-Video Server** running on port 8000
- [ ] **TTS Service** (Chatterbox) running on port 4123
- [ ] **LLM Service** (Ollama or OpenAI) accessible
- [ ] **Redis** running on port 6379

## Step-by-Step Setup

### 1. Start Redis
```bash
# In terminal 1
redis-server
```

### 2. Start LLM Service (Ollama)
```bash
# In terminal 2
ollama serve

# In another terminal, ensure model is available:
ollama pull qwen3:4b
```

### 3. Start TTS Service
```bash
# In terminal 3
cd /home/neil/Documents/text-to-video/chatterbox-tts-api
python start.py
```

### 4. Start Text-to-Video Server
```bash
# In terminal 4
cd /home/neil/Documents/text-to-video/server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Verify All Services
```bash
# Check server
curl http://localhost:8000/api/v1/health

# Check TTS
curl http://localhost:4123/health

# Check Redis
redis-cli ping
```

## Running Integration Tests

### Run All Tests
```bash
cd /home/neil/Documents/text-to-video/tests/integration
python run_integration_tests.py
```

### Run Individual Test Suites

**Performance Tests:**
```bash
pytest test_integration_performance.py -v -s
```

**Reliability Tests:**
```bash
pytest test_integration_reliability.py -v -s
```

**Resource Usage Tests:**
```bash
pytest test_integration_resources.py -v -s
```

### Run Specific Test
```bash
pytest test_integration_performance.py::test_single_request_performance -v -s
```

## Expected Duration

- **Performance Tests**: 5-15 minutes
- **Reliability Tests**: 10-20 minutes
- **Resource Tests**: 5-15 minutes
- **Total**: 20-50 minutes

## View Results

Reports are generated in `tests/integration/reports/`:

```bash
cd reports
ls -l *.md

# View a report
cat integration_performance_report.md
```

## Troubleshooting

### "Connection refused" errors
- **Problem**: One or more services are not running
- **Solution**: Check all services are started (see checklist above)

### Tests timeout
- **Problem**: Services are responding slowly or stuck
- **Solution**: 
  - Check server logs for errors
  - Restart services
  - Increase timeout in `conftest.py`

### "Module not found" errors
- **Problem**: Missing Python dependencies
- **Solution**: 
```bash
cd /home/neil/Documents/text-to-video/tests
pip install -r requirements-tests.txt
```

### Redis connection errors
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server
```

### LLM service errors
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull model if missing
ollama pull qwen3:4b
```

## Environment Variables

You can override default URLs:

```bash
export TEST_SERVER_URL="http://localhost:8000"
export TTS_SERVICE_URL="http://localhost:4123"
export LLM_URL="http://localhost:11434"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

python run_integration_tests.py
```

## Understanding Results

### Performance Report
- **Response Times**: How fast the system processes requests
- **Throughput**: Requests per second the system can handle
- **Latency**: API endpoint response times

### Reliability Report
- **Success Rate**: Percentage of jobs that complete successfully
- **Data Integrity**: Verification that outputs are correct
- **Reliability Score**: Overall system reliability (0-100%)

### Resource Usage Report
- **Memory**: RAM consumption during operations
- **CPU**: Processor utilization
- **Resource Efficiency**: How well the system uses resources

## Tips

1. **Run tests during off-hours** - They consume significant resources
2. **Clean up old files** - Tests create files in server output directories
3. **Monitor system resources** - Use `htop` or `top` to watch resource usage
4. **Check logs** - Server logs provide details on failures
5. **Use fast storage** - SSD recommended for better performance

## Next Steps

After running integration tests:

1. Review all generated reports in `reports/` directory
2. Copy metrics and charts to your academic paper
3. Run tests multiple times for statistical confidence
4. Compare results with unit test results (mocked vs real)
5. Document any issues or interesting findings

## Comparison: Unit vs Integration Tests

| Aspect | Unit Tests (Mocked) | Integration Tests (Real) |
|--------|---------------------|--------------------------|
| Speed | Seconds | Minutes |
| Services | None required | All must be running |
| Accuracy | Simulated | Real-world |
| Cost | Free | May use API credits |
| Purpose | Code correctness | System validation |

**Recommendation**: Use both! Unit tests for development, integration tests before deployment and for academic paper data.
