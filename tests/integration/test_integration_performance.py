"""
Integration Performance Tests - Tests against real server with actual services.

These tests measure real-world performance including:
- Actual LLM inference time
- Real TTS audio generation
- Actual visual asset creation
- Network latency
- File I/O operations
"""
import asyncio
import time
import httpx
import pytest
from typing import Dict, List
from conftest import BASE_URL, wait_for_job_completion, calculate_statistics


@pytest.mark.asyncio
async def test_single_request_performance(
    http_client,
    test_pdf_content,
    test_pdf_path,
    reports_dir,
    verify_services_running
):
    """Test single video generation request performance."""
    print("\n" + "="*80)
    print("TEST 1: Single Request Performance (Real Server)")
    print("="*80)
    
    job_id = f"integration_perf_single_{int(time.time())}"
    
    # Upload PDF
    files = {"file": ("test.pdf", test_pdf_content, "application/pdf")}
    data = {"job_id": job_id}
    
    start_time = time.time()
    
    # Submit job
    response = await http_client.post(
        f"{BASE_URL}/api/v1/video/create",
        files=files,
        data=data
    )
    
    if response.status_code != 200:
        pytest.fail(f"Failed to create job: {response.status_code} - {response.text}")
    
    result = response.json()
    print(f"\n✓ Job submitted: {job_id}")
    
    # Wait for completion
    try:
        final_status = await wait_for_job_completion(http_client, job_id, max_wait=600)
        duration = time.time() - start_time
        
        status = final_status.get("status")
        print(f"\n✓ Job completed in {duration:.2f}s")
        print(f"  Status: {status}")
        print(f"  Progress: {final_status.get('progress', 0)}%")
        
        # Assert success
        assert status == "completed", f"Job failed with status: {status}"
        assert duration < 600, f"Job took too long: {duration:.2f}s"
        
        # Generate report
        report_path = f"{reports_dir}/integration_performance_single.md"
        with open(report_path, 'w') as f:
            f.write("# Integration Performance Test - Single Request\n\n")
            f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Results\n\n")
            f.write(f"- **Total Duration**: {duration:.2f}s\n")
            f.write(f"- **Status**: {status}\n")
            f.write(f"- **Job ID**: {job_id}\n")
            f.write(f"- **PDF**: {test_pdf_path}\n\n")
            f.write(f"## Conclusion\n\n")
            f.write(f"Single video generation completed successfully in {duration:.2f} seconds.\n")
        
        print(f"\n✓ Report saved to: {report_path}")
        
        return {
            "duration": duration,
            "status": status,
            "job_id": job_id
        }
        
    except TimeoutError as e:
        pytest.fail(f"Job timeout: {e}")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_concurrent_requests_performance(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Test concurrent video generation requests."""
    print("\n" + "="*80)
    print("TEST 2: Concurrent Requests Performance (Real Server)")
    print("="*80)
    
    concurrency_levels = [1, 3, 5]
    all_results = {}
    
    for concurrency in concurrency_levels:
        print(f"\n--- Testing {concurrency} concurrent requests ---")
        
        async def process_job(job_num: int):
            """Process a single job."""
            job_id = f"integration_perf_concurrent_{concurrency}_{job_num}_{int(time.time())}"
            
            files = {"file": ("test.pdf", test_pdf_content, "application/pdf")}
            data = {"job_id": job_id}
            
            start = time.time()
            try:
                # Submit job
                response = await http_client.post(
                    f"{BASE_URL}/api/v1/video/create",
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    return {"success": False, "duration": time.time() - start, "error": response.text}
                
                # Wait for completion
                final_status = await wait_for_job_completion(http_client, job_id, max_wait=600)
                duration = time.time() - start
                
                success = final_status.get("status") == "completed"
                print(f"  Job {job_num}: {'✓' if success else '✗'} ({duration:.2f}s)")
                
                return {
                    "success": success,
                    "duration": duration,
                    "job_id": job_id,
                    "status": final_status.get("status")
                }
                
            except Exception as e:
                duration = time.time() - start
                print(f"  Job {job_num}: ✗ Failed - {e}")
                return {"success": False, "duration": duration, "error": str(e)}
        
        # Run concurrent jobs
        overall_start = time.time()
        tasks = [process_job(i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)
        overall_duration = time.time() - overall_start
        
        # Calculate statistics
        durations = [r["duration"] for r in results]
        successes = sum(1 for r in results if r.get("success", False))
        success_rate = (successes / len(results)) * 100
        
        stats = calculate_statistics(durations)
        stats["overall_duration"] = overall_duration
        stats["success_rate"] = success_rate
        stats["successful_jobs"] = successes
        stats["total_jobs"] = len(results)
        
        all_results[concurrency] = stats
        
        print(f"\n  Results:")
        print(f"    Overall Duration: {overall_duration:.2f}s")
        print(f"    Avg Response Time: {stats['avg']:.2f}s")
        print(f"    Success Rate: {success_rate:.1f}%")
        print(f"    Throughput: {len(results) / overall_duration:.2f} req/s")
    
    # Generate report
    report_path = f"{reports_dir}/integration_performance_concurrent.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Performance Test - Concurrent Requests\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Results\n\n")
        
        for concurrency, stats in all_results.items():
            f.write(f"### {concurrency} Concurrent Requests\n\n")
            f.write(f"- **Overall Duration**: {stats['overall_duration']:.2f}s\n")
            f.write(f"- **Average Response Time**: {stats['avg']:.2f}s\n")
            f.write(f"- **P95 Response Time**: {stats['p95']:.2f}s\n")
            f.write(f"- **P99 Response Time**: {stats['p99']:.2f}s\n")
            f.write(f"- **Success Rate**: {stats['success_rate']:.1f}%\n")
            f.write(f"- **Throughput**: {stats['total_jobs'] / stats['overall_duration']:.2f} req/s\n")
            f.write(f"- **Successful**: {stats['successful_jobs']}/{stats['total_jobs']}\n\n")
        
        f.write(f"## Conclusion\n\n")
        f.write(f"Concurrent request testing completed. ")
        f.write(f"The system handled up to {max(all_results.keys())} concurrent requests ")
        f.write(f"with an average success rate of {sum(s['success_rate'] for s in all_results.values()) / len(all_results):.1f}%.\n")
    
    print(f"\n✓ Report saved to: {report_path}")
    
    return all_results


@pytest.mark.asyncio
async def test_api_endpoint_latency(
    http_client,
    reports_dir,
    verify_services_running
):
    """Test latency of various API endpoints."""
    print("\n" + "="*80)
    print("TEST 3: API Endpoint Latency (Real Server)")
    print("="*80)
    
    endpoints = {
        "Health Check": f"{BASE_URL}/api/v1/health",
        "Active Jobs": f"{BASE_URL}/api/v1/video/jobs/active",
    }
    
    results = {}
    
    for endpoint_name, url in endpoints.items():
        print(f"\nTesting: {endpoint_name}")
        latencies = []
        
        # Test each endpoint 10 times
        for i in range(10):
            start = time.time()
            try:
                response = await http_client.get(url)
                latency = (time.time() - start) * 1000  # Convert to ms
                latencies.append(latency)
                
                if i == 0:  # Print first response
                    print(f"  Status: {response.status_code}")
                    
            except Exception as e:
                print(f"  ✗ Request failed: {e}")
        
        stats = calculate_statistics(latencies)
        results[endpoint_name] = stats
        
        print(f"  Avg Latency: {stats['avg']:.2f}ms")
        print(f"  P95 Latency: {stats['p95']:.2f}ms")
    
    # Generate report
    report_path = f"{reports_dir}/integration_performance_latency.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Performance Test - API Endpoint Latency\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Results\n\n")
        
        f.write("| Endpoint | Avg (ms) | Min (ms) | Max (ms) | P95 (ms) | P99 (ms) |\n")
        f.write("|----------|----------|----------|----------|----------|----------|\n")
        
        for endpoint_name, stats in results.items():
            f.write(f"| {endpoint_name} | {stats['avg']:.2f} | {stats['min']:.2f} | ")
            f.write(f"{stats['max']:.2f} | {stats['p95']:.2f} | {stats['p99']:.2f} |\n")
        
        f.write(f"\n## Conclusion\n\n")
        f.write(f"API endpoint latency measurements completed. ")
        avg_latency = sum(s['avg'] for s in results.values()) / len(results)
        f.write(f"Average latency across all endpoints: {avg_latency:.2f}ms.\n")
    
    print(f"\n✓ Report saved to: {report_path}")
    
    return results


@pytest.mark.asyncio
async def test_generate_performance_report(
    http_client,
    test_pdf_content,
    test_pdf_path,
    reports_dir,
    verify_services_running
):
    """Generate comprehensive performance report."""
    print("\n" + "="*80)
    print("INTEGRATION PERFORMANCE TESTING SUITE")
    print("="*80)
    
    # Run all tests
    single_result = await test_single_request_performance(
        http_client, test_pdf_content, test_pdf_path, reports_dir, verify_services_running
    )
    
    concurrent_results = await test_concurrent_requests_performance(
        http_client, test_pdf_content, reports_dir, verify_services_running
    )
    
    latency_results = await test_api_endpoint_latency(
        http_client, reports_dir, verify_services_running
    )
    
    # Generate comprehensive report
    report_path = f"{reports_dir}/integration_performance_report.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Performance Test Report\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Server**: {BASE_URL}\n")
        f.write(f"**Test Type**: Integration (Real Services)\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Single Request**: {single_result['duration']:.2f}s\n")
        f.write(f"- **Max Concurrency Tested**: {max(concurrent_results.keys())} requests\n")
        f.write(f"- **Average API Latency**: {sum(s['avg'] for s in latency_results.values()) / len(latency_results):.2f}ms\n\n")
        
        f.write("## 1. Single Request Performance\n\n")
        f.write(f"- **Duration**: {single_result['duration']:.2f}s\n")
        f.write(f"- **Status**: {single_result['status']}\n")
        f.write(f"- **Job ID**: {single_result['job_id']}\n\n")
        
        f.write("## 2. Concurrent Request Performance\n\n")
        for concurrency, stats in concurrent_results.items():
            f.write(f"### {concurrency} Concurrent Requests\n\n")
            f.write(f"- Overall Duration: {stats['overall_duration']:.2f}s\n")
            f.write(f"- Avg Response Time: {stats['avg']:.2f}s\n")
            f.write(f"- P95 Response Time: {stats['p95']:.2f}s\n")
            f.write(f"- Success Rate: {stats['success_rate']:.1f}%\n")
            f.write(f"- Throughput: {stats['total_jobs'] / stats['overall_duration']:.2f} req/s\n\n")
        
        f.write("## 3. API Endpoint Latency\n\n")
        f.write("| Endpoint | Avg (ms) | P95 (ms) | P99 (ms) |\n")
        f.write("|----------|----------|----------|----------|\n")
        for endpoint_name, stats in latency_results.items():
            f.write(f"| {endpoint_name} | {stats['avg']:.2f} | {stats['p95']:.2f} | {stats['p99']:.2f} |\n")
        
        f.write("\n## Conclusions\n\n")
        f.write("Integration performance testing completed successfully against real services. ")
        f.write("All metrics reflect actual system performance including network latency, ")
        f.write("LLM inference, TTS generation, and file I/O operations.\n")
    
    print(f"\n" + "="*80)
    print(f"✓ Comprehensive report saved to: {report_path}")
    print("="*80)
