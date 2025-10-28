# Testing Strategy Overview

This document explains the two different testing approaches available in this repository.

## Two Testing Approaches

### 1. Unit Tests with Mocks (`/tests/`)

**Location**: `/tests/` (main tests folder)

**Approach**: Tests use **mocked services** - all external dependencies (LLM, TTS, Visual services) are simulated.

**Characteristics:**
- ⚡ **Fast**: Complete in seconds to minutes
- 🔧 **No dependencies**: No services need to be running
- 🎯 **Focused**: Tests specific code paths and logic
- 💰 **Free**: No API costs
- 📊 **Consistent**: Same results every time
- 🚀 **Development-friendly**: Run anytime during coding

**Files:**
- `conftest.py` - Mock fixtures for all services
- `test_performance.py` - Mocked performance tests
- `test_reliability.py` - Mocked reliability tests  
- `test_resources.py` - Mocked resource tests
- `run_all_tests.py` - Runner script

**When to use:**
- During active development
- For CI/CD pipelines
- For quick validation of code changes
- When services are unavailable

**Run command:**
```bash
cd /home/neil/Documents/text-to-video/tests
python run_all_tests.py
```

### 2. Integration Tests with Real Services (`/tests/integration/`)

**Location**: `/tests/integration/` (integration folder)

**Approach**: Tests use **real, running services** - actual LLM inference, TTS generation, and visual asset creation.

**Characteristics:**
- 🐢 **Slow**: Takes 20-50 minutes
- 🔌 **Dependencies**: All services must be running (Redis, Ollama, TTS, Server)
- 🌍 **Real-world**: Tests actual system behavior
- 💳 **May have costs**: Uses API credits if using paid services
- 📈 **Variable**: Results depend on service performance
- 🎓 **Production-like**: Validates complete system

**Files:**
- `conftest.py` - Real service configuration
- `test_integration_performance.py` - Real performance tests
- `test_integration_reliability.py` - Real reliability tests
- `test_integration_resources.py` - Real resource tests
- `run_integration_tests.py` - Runner script
- `README.md`, `QUICKSTART.md`, `INTEGRATION_TESTS_SUMMARY.md` - Documentation

**When to use:**
- Before deployment to production
- For academic paper data collection
- To validate system behavior end-to-end
- When you need real-world metrics

**Run command:**
```bash
cd /home/neil/Documents/text-to-video/tests/integration
python run_integration_tests.py
```

## Detailed Comparison

| Aspect | Unit Tests (Mocked) | Integration Tests (Real) |
|--------|---------------------|--------------------------|
| **Execution Time** | < 1 minute | 20-50 minutes |
| **Setup Required** | None | Start Redis, Ollama, TTS, Server |
| **Dependencies** | pytest, psutil | pytest, psutil, httpx + all services |
| **Data Accuracy** | Simulated | Real-world |
| **Repeatability** | 100% consistent | Variable (depends on services) |
| **Cost** | $0 | Potential API costs |
| **Network Required** | No | Yes (localhost) |
| **Failure Modes** | Code bugs only | Code bugs + service issues |
| **CI/CD Friendly** | Yes | No (too slow, needs services) |
| **Debugging** | Easy | Complex |
| **Resource Usage** | Low | High |
| **Academic Value** | Low | High |

## Which Tests to Run?

### For Development (Daily)
→ **Use Unit Tests (Mocked)**
- Fast feedback loop
- No setup required
- Catches code errors quickly

### Before Deployment (Weekly/Monthly)
→ **Use Integration Tests (Real)**
- Validates entire system
- Catches integration issues
- Confirms production readiness

### For Academic Paper
→ **Use Both, Emphasize Integration Tests**
- Unit tests show code quality
- Integration tests provide real metrics
- Comparison shows testing thoroughness

## Workflow Recommendations

### During Development
```bash
# Make code changes
# Run unit tests to verify
cd tests
python run_all_tests.py  # Takes < 1 minute

# If pass, commit changes
```

### Before Submitting Paper
```bash
# Start all services
# Run integration tests
cd tests/integration
python run_integration_tests.py  # Takes 20-50 minutes

# Use generated reports in paper
# Compare with unit test results
```

### Complete Testing Cycle
```bash
# 1. Run unit tests first (quick validation)
cd tests
python run_all_tests.py

# 2. If unit tests pass, run integration tests
cd integration
python run_integration_tests.py

# 3. Compare results
# 4. Document any discrepancies
# 5. Use data in paper
```

## Generated Reports

### Unit Test Reports (`/tests/reports/`)
- `performance_report.md` - Mocked performance metrics
- `reliability_report.md` - Mocked reliability analysis
- `resources_report.md` - Mocked resource usage

### Integration Test Reports (`/tests/integration/reports/`)
- `integration_performance_report.md` - Real performance metrics
- `integration_reliability_report.md` - Real reliability analysis
- `integration_resources_report.md` - Real resource usage

## For Your Academic Paper

### Recommended Structure

**1. Testing Methodology Section**
```
We employed two testing approaches:

1. Unit Testing with Mocked Services: Fast, isolated tests using 
   simulated external dependencies to validate code correctness.

2. Integration Testing with Real Services: Comprehensive end-to-end
   tests using actual LLM, TTS, and visual generation services to
   measure real-world system performance.
```

**2. Present Both Results**
```
Table X: Performance Comparison

| Metric | Unit Tests | Integration Tests | Difference |
|--------|-----------|-------------------|------------|
| Avg Response Time | X.Xs | Y.Ys | Z% |
| Success Rate | 100% | 98% | -2% |
| Memory Usage | X MB | Y MB | +Z% |
```

**3. Analyze Differences**
```
Integration tests revealed approximately X% slower response times
compared to unit tests, attributed to actual LLM inference latency
and network overhead. The Y% difference in memory usage reflects
real service communication buffers and data serialization overhead.
```

**4. Conclusions**
```
Both testing approaches validated system correctness. Unit tests
confirmed code logic integrity, while integration tests demonstrated
production-readiness with X% success rate under real-world conditions.
```

## Quick Reference

### Run Unit Tests (Mocked)
```bash
cd /home/neil/Documents/text-to-video/tests
python run_all_tests.py
```

### Run Integration Tests (Real Services)
```bash
# First, start all services (see integration/QUICKSTART.md)
cd /home/neil/Documents/text-to-video/tests/integration
python run_integration_tests.py
```

### View Results
```bash
# Unit test reports
ls -l tests/reports/*.md

# Integration test reports
ls -l tests/integration/reports/*.md
```

## Troubleshooting

### Unit Tests Failing
- **Problem**: Import errors, module not found
- **Solution**: Check Python path in `conftest.py`, ensure dependencies installed

### Integration Tests Failing
- **Problem**: Connection refused, service not available
- **Solution**: Ensure all services running (see `integration/QUICKSTART.md`)

### Both Tests Failing
- **Problem**: Code bugs, logic errors
- **Solution**: Fix code issues, unit tests should pass first

## Maintenance

### Adding New Tests

**For Unit Tests (Mocked):**
1. Add mock fixtures to `/tests/conftest.py`
2. Create test functions using mocked services
3. Update report generation functions

**For Integration Tests (Real):**
1. Verify service endpoints in `/tests/integration/conftest.py`
2. Create test functions using HTTP client
3. Add proper wait/timeout handling
4. Update report generation functions

### Updating Documentation

When changing tests, update:
- This file (`TESTING_STRATEGY.md`)
- `/tests/README.md` (for unit tests)
- `/tests/integration/README.md` (for integration tests)

## Conclusion

**Use unit tests for speed and development**, **use integration tests for validation and real data**.

Both are valuable:
- Unit tests = Code quality assurance
- Integration tests = System validation

For your academic paper, integration test data is more valuable because it reflects real-world system performance. However, mentioning both approaches demonstrates thoroughness in your testing methodology.

---

**Remember**: 
- Unit tests ≠ Bad (they're essential for development)
- Integration tests ≠ Better (they're slower and more complex)
- Both together = Comprehensive testing strategy ✓
