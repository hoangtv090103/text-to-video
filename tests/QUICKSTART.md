# Quick Start Guide - Testing Suite

## 🚀 Running the Tests

### Method 1: Run All Tests (Recommended)

```bash
cd /home/neil/Documents/text-to-video/tests
python run_all_tests.py
```

This will:
- Run all three test suites (Performance, Reliability, Resources)
- Generate comprehensive Markdown reports
- Display summary of results

### Method 2: Run Individual Test Suites

```bash
cd /home/neil/Documents/text-to-video

# Performance tests
pytest tests/test_performance.py::test_generate_performance_report -v -s

# Reliability tests
pytest tests/test_reliability.py::test_generate_reliability_report -v -s

# Resource usage tests
pytest tests/test_resources.py::test_generate_resources_report -v -s
```

### Method 3: Run Specific Test Cases

```bash
# Run only concurrent request testing
pytest tests/test_performance.py::test_concurrent_requests -v -s

# Run only TTS failure recovery testing
pytest tests/test_reliability.py::test_tts_service_failure_recovery -v -s

# Run only memory leak detection
pytest tests/test_resources.py::test_memory_leak_detection -v -s
```

## 📊 Viewing Results

After running tests, reports are generated in:
```
tests/reports/
├── performance_report.md
├── reliability_report.md
└── resources_report.md
```

Open them with any Markdown viewer or text editor:
```bash
# View in terminal
cat tests/reports/performance_report.md

# Open in VS Code
code tests/reports/performance_report.md

# Convert to PDF (requires pandoc)
pandoc tests/reports/performance_report.md -o performance_report.pdf
```

## 📝 For Your Paper

### Copy Relevant Sections

Each report contains:
1. **Executive Summary** - Key findings for abstract/introduction
2. **Detailed Results Tables** - For results section
3. **Analysis** - For discussion section
4. **Charts** - ASCII charts (convert to graphs if needed)

### Example Citations

```
Performance Testing Results:
- Response time: 0.xxx seconds (average)
- Throughput: xx.x requests/second
- Success rate: 95.x% under normal load

Reliability Testing Results:
- System reliability: 95.x%
- Error recovery rate: xx.x%
- Data integrity: 90.x%

Resource Usage Results:
- Memory per job: xxx MB
- CPU utilization: xx.x%
- Infrastructure cost: $x.xx per 1000 jobs
```

## 🐛 Troubleshooting

### Import Errors
```bash
# Ensure you're in the correct directory
cd /home/neil/Documents/text-to-video

# Install dependencies
pip install pytest pytest-asyncio psutil
```

### Module Not Found
```bash
# Add parent directory to Python path
export PYTHONPATH=/home/neil/Documents/text-to-video:$PYTHONPATH
```

### Test Failures
- Check that the PDF file exists: `/home/neil/Documents/text-to-video/2507.08034v1.pdf`
- Ensure all mock fixtures are loaded correctly
- Review error output for specific issues

## 💡 Tips

1. **Run tests multiple times** for statistical significance
2. **Adjust concurrency levels** in test files if needed
3. **Export reports to different formats** (PDF, HTML, Word)
4. **Take screenshots** of terminal output for appendix

## 📧 Questions?

Review the main README.md in the tests directory for more details.

---

**Happy Testing! 🎉**
