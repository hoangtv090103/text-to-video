# Testing Suite for Text-to-Video Service

This directory contains comprehensive testing suites for evaluating the text-to-video service across three critical dimensions: **Performance**, **Reliability**, and **Resource Usage**.

## 📁 Test Structure

```
tests/
├── conftest.py                 # Shared test fixtures and mocks
├── test_data_helper.py         # Test utilities and data generators
├── test_performance.py         # Performance testing suite
├── test_reliability.py         # Reliability testing suite
├── test_resources.py           # Resource usage testing suite
├── reports/                    # Generated test reports
│   ├── performance_report.md
│   ├── reliability_report.md
│   └── resources_report.md
└── README.md                   # This file
```

## 🎯 Test Objectives

### 1. Performance Testing (`test_performance.py`)
Evaluates processing performance and scalability:
- **Response Time**: End-to-end latency measurements
- **Concurrent Requests**: System behavior under load (1, 5, 10, 20, 50 concurrent jobs)
- **Throughput**: Requests per second capacity
- **API Latency**: Individual endpoint performance

### 2. Reliability Testing (`test_reliability.py`)
Validates system robustness and error recovery:
- **Success Rate**: Normal operation reliability
- **Error Recovery**: Retry mechanisms and circuit breakers
- **Service Failures**: TTS/LLM/Redis failure scenarios
- **Data Integrity**: Consistency across partial failures
- **Job Cancellation**: Graceful handling of cancelled jobs

### 3. Resource Usage Testing (`test_resources.py`)
Analyzes resource consumption patterns:
- **Memory Usage**: Baseline, peak, and leak detection
- **CPU Utilization**: Processing efficiency
- **Network Bandwidth**: I/O patterns and optimization
- **Cache Efficiency**: Hit rates and savings
- **Infrastructure Costs**: Estimation per job/month

## 🚀 Running the Tests

### Prerequisites

Install required dependencies:

```bash
pip install pytest pytest-asyncio psutil
```

### Run All Tests

```bash
# Run all test suites
pytest tests/ -v -s

# Run specific test suite
pytest tests/test_performance.py -v -s
pytest tests/test_reliability.py -v -s
pytest tests/test_resources.py -v -s
```

### Generate Reports Only

```bash
# Run the comprehensive report generation tests
pytest tests/test_performance.py::test_generate_performance_report -v -s
pytest tests/test_reliability.py::test_generate_reliability_report -v -s
pytest tests/test_resources.py::test_generate_resources_report -v -s
```

## 📊 Test Reports

After running the tests, detailed Markdown reports are generated in `tests/reports/`:

### Performance Report (`performance_report.md`)
- Response time statistics (min, avg, max, P95, P99)
- Concurrent load testing results
- API endpoint latency breakdown
- Component-level performance analysis
- Scalability recommendations

### Reliability Report (`reliability_report.md`)
- Success rate under normal conditions
- Error recovery metrics and MTTR
- Circuit breaker effectiveness
- Partial failure handling
- Data integrity validation
- Reliability score calculation

### Resource Usage Report (`resources_report.md`)
- Memory consumption patterns
- CPU utilization analysis
- Network bandwidth usage
- Cache efficiency metrics
- Infrastructure cost estimation
- Optimization recommendations

## 🧪 Test Configuration

### Mocked Services
All tests use mocked external services for isolation and reproducibility:
- **LLM Service**: Mock script generation (5 scenes)
- **TTS Service**: Mock audio generation
- **Visual Service**: Mock image generation
- **Redis**: In-memory mock job tracking

### Test Data
- **Document**: `2507.08034v1.pdf` (Academic paper)
- **Scenes**: 5 per job (mixed visual types)
- **Concurrency Levels**: 1, 5, 10, 20, 50
- **Iterations**: 10-20 per test case

## 📈 Expected Results

### Performance Benchmarks
- Single request: < 2s response time
- API endpoints: < 500ms P95 latency
- Success rate: ≥ 95% under normal load
- Throughput: > 10 req/s at 50 concurrency

### Reliability Targets
- Normal operation: ≥ 95% success rate
- Recovery rate: ≥ 60% from transient failures
- Circuit breaker: Active protection
- Data integrity: ≥ 90% maintained

### Resource Limits
- Memory per job: < 100 MB increase
- CPU utilization: < 80% average
- No memory leaks: < 10% growth over 20 iterations
- Cache hit rate: ≥ 40% average

## 🔍 Test Scenarios

### Performance Test Scenarios
1. **Single Request**: Baseline performance measurement
2. **Concurrent Load**: 1→5→10→20→50 concurrent jobs
3. **API Latency**: Health, status, and listing endpoints
4. **Component Speed**: LLM, TTS, visual generation timing

### Reliability Test Scenarios
1. **Normal Operation**: 20 jobs baseline success rate
2. **TTS Failures**: 30% failure rate with retry
3. **LLM Circuit Breaker**: Complete service failure
4. **Partial Failures**: Some scenes fail, job continues
5. **Job Cancellation**: Mid-processing cancellation
6. **Data Integrity**: Asset and metadata validation

### Resource Test Scenarios
1. **Baseline**: System idle state
2. **Single Job**: Resource profile per job
3. **Concurrent Load**: 1→5→10→20 jobs resource scaling
4. **Memory Leak**: 20 sequential jobs trend analysis
5. **Cache Efficiency**: Repeated identical inputs
6. **Connection Pooling**: Network overhead reduction

## 📝 Writing Academic Paper

### Using Test Results

The reports are formatted for easy inclusion in academic papers:

1. **Methodology Section**:
   - Reference test configuration and mocking strategy
   - Cite test scenarios and sample sizes

2. **Results Section**:
   - Extract tables and metrics from reports
   - Include ASCII charts or convert to graphs
   - Reference reliability scores and cost estimates

3. **Discussion Section**:
   - Analyze optimization impact
   - Compare with baseline (no optimizations)
   - Discuss scalability characteristics

### Key Metrics for Paper

**Performance**:
- Response time: {avg}s ± {stddev}s
- Throughput: {max} requests/second
- P95 latency: {value}ms

**Reliability**:
- Success rate: {percentage}%
- MTTR: {seconds}s
- Recovery rate: {percentage}%

**Resources**:
- Memory per job: {MB} MB
- Cost per 1000 jobs: ${amount}
- Cache hit rate: {percentage}%

## 🛠 Extending Tests

### Adding New Test Cases

1. Add test function to appropriate file:
```python
@pytest.mark.asyncio
async def test_new_scenario(mock_file_context, ...):
    # Test implementation
    pass
```

2. Update report generator to include new metrics

3. Document in this README

### Adding New Metrics

1. Extend `ResourceMetricsCollector` or create new collector
2. Update report template with new sections
3. Add visualization (ASCII charts, tables)

## 📚 References

- **pytest**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **psutil**: https://psutil.readthedocs.io/

## 🤝 Contributing

When adding tests:
1. Follow existing naming conventions
2. Include docstrings with clear descriptions
3. Update this README with new scenarios
4. Ensure reports generate correctly

## 📧 Support

For questions about the testing suite, please contact the development team.

---

**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}  
**Test Framework**: pytest 7.x + pytest-asyncio  
**Python Version**: 3.10+
