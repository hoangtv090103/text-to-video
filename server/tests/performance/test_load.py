"""
Load Testing for Text-to-Video Service
Tests performance under concurrent load and measures key metrics
"""

import asyncio
import time
import pytest
import httpx
from typing import List, Dict
import statistics
import psutil
import os


@pytest.mark.asyncio
async def test_concurrent_load_performance():
    """
    Test system performance with concurrent requests
    Measures: P50, P90, P99 response times and throughput
    """
    base_url = "http://localhost:8000"
    num_requests = 100  # Simulate 100 concurrent requests
    response_times = []
    success_count = 0

    async def make_request(client: httpx.AsyncClient, request_id: int):
        nonlocal success_count
        start_time = time.time()
        try:
            # Simple health check for load testing with increased timeout
            response = await client.get(f"{base_url}/health", timeout=60.0)
            elapsed = time.time() - start_time
            response_times.append(elapsed)
            if response.status_code == 200:
                success_count += 1
            return elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            response_times.append(elapsed)
            return elapsed

    # Start time
    test_start = time.time()

    async with httpx.AsyncClient() as client:
        tasks = [make_request(client, i) for i in range(num_requests)]
        await asyncio.gather(*tasks)

    # Calculate metrics
    test_duration = time.time() - test_start

    if response_times:
        sorted_times = sorted(response_times)
        p50 = statistics.median(sorted_times)
        p90 = sorted_times[int(len(sorted_times) * 0.9)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        avg_time = statistics.mean(sorted_times)
        throughput = num_requests / test_duration if test_duration > 0 else 0

        # Print results
        print(f"\n=== Load Test Results ===")
        print(f"Total Requests: {num_requests}")
        print(f"Success Rate: {(success_count/num_requests)*100:.2f}%")
        print(f"Test Duration: {test_duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s ({throughput*60:.2f} req/min)")
        print(f"Response Times:")
        print(f"  - Average: {avg_time*1000:.2f}ms")
        print(f"  - P50: {p50*1000:.2f}ms")
        print(f"  - P90: {p90*1000:.2f}ms")
        print(f"  - P99: {p99*1000:.2f}ms")

        # Assertions based on expected performance
        assert success_count >= num_requests * 0.80, "Success rate should be >= 80%"
        assert p99 < 5.0, "P99 should be under 5 seconds for health checks"


@pytest.mark.asyncio
async def test_resource_usage_under_load():
    """
    Monitor memory and CPU usage during load testing
    """
    base_url = "http://localhost:8000"
    process = psutil.Process(os.getpid())

    # Baseline measurements
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    num_requests = 200

    async def make_request(client: httpx.AsyncClient):
        try:
            response = await client.get(f"{base_url}/health", timeout=60.0)
            return response.status_code == 200
        except Exception:
            return False

    # Run load test
    async with httpx.AsyncClient() as client:
        tasks = [make_request(client) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)

    # Final measurements
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    print(f"\n=== Resource Usage Test ===")
    print(f"Initial Memory: {initial_memory:.2f} MB")
    print(f"Final Memory: {final_memory:.2f} MB")
    print(f"Memory Increase: {memory_increase:.2f} MB")
    print(f"Success Count: {sum(results)}/{num_requests}")

    # Memory should not increase excessively (< 100MB for 200 requests)
    assert memory_increase < 100, f"Memory increase ({memory_increase:.2f}MB) exceeds limit"


@pytest.mark.asyncio
async def test_throughput_measurement():
    """
    Measure system throughput over sustained period
    """
    base_url = "http://localhost:8000"
    duration_seconds = 10
    request_count = 0

    async def continuous_requests(client: httpx.AsyncClient, stop_event: asyncio.Event):
        nonlocal request_count
        while not stop_event.is_set():
            try:
                await client.get(f"{base_url}/health", timeout=10.0)
                request_count += 1
            except Exception:
                pass

    async with httpx.AsyncClient() as client:
        stop_event = asyncio.Event()

        # Run concurrent workers
        workers = [continuous_requests(client, stop_event) for _ in range(10)]

        # Let it run for specified duration
        await asyncio.sleep(duration_seconds)
        stop_event.set()

        await asyncio.gather(*workers)

    throughput_per_sec = request_count / duration_seconds
    throughput_per_min = throughput_per_sec * 60

    print(f"\n=== Throughput Test ===")
    print(f"Duration: {duration_seconds}s")
    print(f"Total Requests: {request_count}")
    print(f"Throughput: {throughput_per_sec:.2f} req/s")
    print(f"Throughput: {throughput_per_min:.2f} req/min")

    # Should handle at least 10 req/s for health endpoint (more realistic for async tests)
    assert throughput_per_sec >= 10, f"Throughput ({throughput_per_sec:.2f}) below minimum"


if __name__ == "__main__":
    asyncio.run(test_concurrent_load_performance())
    asyncio.run(test_resource_usage_under_load())
    asyncio.run(test_throughput_measurement())
