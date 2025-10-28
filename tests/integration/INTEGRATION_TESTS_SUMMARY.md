# Integration Tests Summary

## Overview

The integration testing suite in `/tests/integration/` provides comprehensive testing against **real, running services** (no mocks). These tests validate the entire text-to-video system in a production-like environment.

## Created Files

### Documentation (3 files)
1. **README.md** - Complete documentation with prerequisites, setup, and troubleshooting
2. **QUICKSTART.md** - Step-by-step guide for running tests quickly
3. **INTEGRATION_TESTS_SUMMARY.md** (this file) - High-level overview

### Configuration (1 file)
4. **conftest.py** - pytest fixtures and helper functions for integration tests

### Test Files (3 files)
5. **test_integration_performance.py** - Performance testing with real services
6. **test_integration_reliability.py** - Reliability and error handling tests
7. **test_integration_resources.py** - Resource consumption measurements

### Runner (1 file)
8. **run_integration_tests.py** - Automated test execution script

**Total: 8 files**

## Test Coverage

### Performance Tests
- ✅ Single request response time (real LLM, TTS, visual generation)
- ✅ Concurrent request handling (1, 3, 5 concurrent jobs)
- ✅ API endpoint latency measurements
- ✅ Real-world throughput calculation

### Reliability Tests
- ✅ Normal operation success rate (5 sequential jobs)
- ✅ Data integrity verification
- ✅ Job status tracking accuracy
- ✅ Error handling and recovery

### Resource Usage Tests
- ✅ Baseline resource consumption (idle state)
- ✅ Single job resource profiling (memory, CPU)
- ✅ Concurrent job resource scaling (1, 3, 5 jobs)
- ✅ Resource efficiency analysis

## Key Differences from Unit Tests

| Feature | Unit Tests (`/tests/`) | Integration Tests (`/tests/integration/`) |
|---------|------------------------|-------------------------------------------|
| **Services** | Mocked | Real (must be running) |
| **Speed** | Fast (< 1 minute) | Slow (20-50 minutes) |
| **Dependencies** | None | All services required |
| **Accuracy** | Simulated | Real-world |
| **Cost** | Free | May consume API credits |
| **Complexity** | Simple | Complex |
| **Reliability** | Always consistent | Can fail due to external factors |
| **Purpose** | Code validation | System validation |

## How to Use

### Quick Start (5 steps)
1. **Start all services** (Redis, Ollama, TTS, Server)
2. **Verify services** are accessible
3. **Run tests**: `cd tests/integration && python run_integration_tests.py`
4. **Review reports** in `reports/` directory
5. **Use data** in academic paper

### For Academic Paper

Integration tests provide **real-world metrics** for your paper:

- **Performance Section**: Use response times, throughput, concurrency data
- **Reliability Section**: Use success rates, error recovery data
- **Resource Section**: Use memory/CPU consumption, efficiency metrics
- **Comparison**: Compare mocked vs real performance

All reports are in Markdown format, ready to be adapted for your paper.

## Generated Reports

After running tests, find reports in `tests/integration/reports/`:

1. **integration_performance_report.md** - Comprehensive performance analysis
2. **integration_reliability_report.md** - Reliability and integrity analysis
3. **integration_resources_report.md** - Resource consumption analysis
4. Individual test reports (performance_single, concurrent, latency, etc.)

## Requirements

### System Requirements
- **Python**: 3.10+
- **Memory**: 4GB+ RAM recommended
- **Storage**: 2GB+ free space for test outputs
- **Network**: Localhost connections

### Service Requirements
- **Redis**: 6.0+
- **Ollama**: Latest version with `qwen3:4b` model
- **TTS Service**: Chatterbox TTS API running
- **Server**: Text-to-video server running

### Python Dependencies
```bash
pip install -r ../requirements-tests.txt
```

Key packages:
- pytest (testing framework)
- pytest-asyncio (async test support)
- httpx (HTTP client)
- psutil (system monitoring)

## Test Execution Time

Typical execution times:

- **Performance Tests**: 5-15 minutes
  - Single request: 2-5 minutes
  - Concurrent (3 levels): 3-10 minutes
  - Latency: < 1 minute

- **Reliability Tests**: 10-20 minutes
  - Normal operation (5 jobs): 10-15 minutes
  - Data integrity: 2-5 minutes

- **Resource Tests**: 5-15 minutes
  - Baseline: < 1 minute
  - Single job: 2-5 minutes
  - Concurrent (3 levels): 3-10 minutes

**Total**: 20-50 minutes for all tests

## Troubleshooting Guide

### Common Issues

**1. Connection Errors**
```
Problem: Cannot connect to server/services
Solution: Verify all services are running and accessible
```

**2. Test Timeouts**
```
Problem: Tests exceed time limits
Solution: Check service logs, restart services, increase timeouts
```

**3. Low Success Rates**
```
Problem: Many jobs fail during testing
Solution: Check LLM/TTS service availability, verify API keys
```

**4. High Resource Usage**
```
Problem: System becomes slow during tests
Solution: Close unnecessary applications, use machine with more resources
```

## Best Practices

1. **Run on dedicated system** - Avoid running other heavy applications
2. **Check logs first** - Review server logs before running tests
3. **Multiple runs** - Run tests 2-3 times for statistical confidence
4. **Document environment** - Note system specs, service versions
5. **Compare results** - Compare with unit test results
6. **Clean up** - Remove old test files periodically

## For Your Academic Paper

### Data to Extract

**Performance Metrics:**
- Response time: X seconds per video
- Throughput: Y requests/second
- Scalability: Handles Z concurrent requests

**Reliability Metrics:**
- Success rate: X% under normal conditions
- Data integrity: 100% verified
- Error recovery: Automatic retry on failures

**Resource Metrics:**
- Memory: X MB per job
- CPU: Y% average utilization
- Efficiency: Z jobs per GB RAM

### Sample Statements for Paper

> "Integration testing with real services showed an average response time of X seconds for single video generation requests."

> "The system maintained a Y% success rate when processing Z concurrent video generation jobs."

> "Resource profiling revealed an average memory consumption of X MB per video generation task, with peak CPU utilization of Y%."

> "Comparison between unit tests (mocked services) and integration tests (real services) showed a Z% difference in performance metrics, demonstrating [insight]."

## Maintenance

### Regular Updates
- Update service URLs in `conftest.py` if ports change
- Adjust timeouts if services become faster/slower
- Add new tests as features are added
- Update documentation as system evolves

### Monitoring
- Track test execution times (should remain consistent)
- Monitor success rates (sudden drops indicate issues)
- Review resource trends (increases may indicate memory leaks)

## Support

For issues or questions:
1. Check `README.md` for detailed documentation
2. Review `QUICKSTART.md` for setup steps
3. Examine test logs for error details
4. Check server logs for service issues

## Conclusion

The integration test suite provides **real-world validation** of your text-to-video system. Unlike unit tests with mocks, these tests verify that:

✅ All services work together correctly
✅ Performance meets expectations under real load
✅ System is reliable with actual API calls
✅ Resources are managed efficiently

Use these tests to generate authentic data for your academic paper and to ensure your system is production-ready.

---

**Created**: October 28, 2025
**Purpose**: Academic paper testing + System validation
**Approach**: Real services, no mocks, comprehensive analysis
