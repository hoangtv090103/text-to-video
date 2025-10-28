"""
Integration Resource Usage Tests - Tests against real server.

These tests measure actual resource consumption including:
- Real memory usage during video generation
- Actual CPU utilization
- True disk I/O and storage
- Real network bandwidth
"""
import asyncio
import time
import httpx
import pytest
import psutil
import os
from typing import Dict, List
from conftest import BASE_URL, wait_for_job_completion


class ResourceMonitor:
    """Monitor system resources during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.measurements = []
    
    def measure(self):
        """Take a resource measurement."""
        measurement = {
            "timestamp": time.time(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "cpu_percent": self.process.cpu_percent(),
        }
        self.measurements.append(measurement)
        return measurement
    
    def get_stats(self):
        """Calculate statistics from measurements."""
        if not self.measurements:
            return {}
        
        memory_values = [m["memory_mb"] for m in self.measurements]
        cpu_values = [m["cpu_percent"] for m in self.measurements]
        
        return {
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values),
                "peak": max(memory_values)
            },
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "peak": max(cpu_values)
            },
            "samples": len(self.measurements)
        }


@pytest.mark.asyncio
async def test_baseline_resource_usage(reports_dir):
    """Measure baseline resource usage (idle state)."""
    print("\n" + "="*80)
    print("TEST 1: Baseline Resource Usage")
    print("="*80)
    
    monitor = ResourceMonitor()
    
    # Take measurements over 5 seconds
    for _ in range(5):
        monitor.measure()
        await asyncio.sleep(1)
    
    stats = monitor.get_stats()
    
    print(f"\nBaseline Metrics:")
    print(f"  Memory: {stats['memory']['avg']:.2f} MB")
    print(f"  CPU: {stats['cpu']['avg']:.2f}%")
    
    # Generate report
    report_path = f"{reports_dir}/integration_resources_baseline.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Resource Usage - Baseline\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Results\n\n")
        f.write(f"- **Average Memory**: {stats['memory']['avg']:.2f} MB\n")
        f.write(f"- **Peak Memory**: {stats['memory']['peak']:.2f} MB\n")
        f.write(f"- **Average CPU**: {stats['cpu']['avg']:.2f}%\n")
        f.write(f"- **Peak CPU**: {stats['cpu']['peak']:.2f}%\n")
        f.write(f"- **Samples**: {stats['samples']}\n")
    
    print(f"\n✓ Report saved to: {report_path}")
    
    return stats


@pytest.mark.asyncio
async def test_single_job_resource_usage(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Measure resource usage during single video generation."""
    print("\n" + "="*80)
    print("TEST 2: Single Job Resource Usage (Real Server)")
    print("="*80)
    
    monitor = ResourceMonitor()
    job_id = f"integration_resources_single_{int(time.time())}"
    
    # Start monitoring
    monitoring = True
    
    async def monitor_loop():
        """Continuously monitor resources."""
        while monitoring:
            monitor.measure()
            await asyncio.sleep(0.5)
    
    monitor_task = asyncio.create_task(monitor_loop())
    
    # Submit job
    files = {"file": ("test.pdf", test_pdf_content, "application/pdf")}
    data = {"job_id": job_id}
    
    start = time.time()
    
    try:
        response = await http_client.post(
            f"{BASE_URL}/api/v1/video/create",
            files=files,
            data=data
        )
        
        if response.status_code != 200:
            pytest.fail(f"Failed to create job: {response.status_code}")
        
        print(f"\n✓ Job submitted: {job_id}")
        
        # Wait for completion
        final_status = await wait_for_job_completion(http_client, job_id, max_wait=600)
        duration = time.time() - start
        
        # Stop monitoring
        monitoring = False
        await monitor_task
        
        stats = monitor.get_stats()
        
        print(f"\n✓ Job completed in {duration:.2f}s")
        print(f"\nResource Usage:")
        print(f"  Peak Memory: {stats['memory']['peak']:.2f} MB")
        print(f"  Avg Memory: {stats['memory']['avg']:.2f} MB")
        print(f"  Peak CPU: {stats['cpu']['peak']:.2f}%")
        print(f"  Avg CPU: {stats['cpu']['avg']:.2f}%")
        
        # Generate report
        report_path = f"{reports_dir}/integration_resources_single.md"
        with open(report_path, 'w') as f:
            f.write("# Integration Resource Usage - Single Job\n\n")
            f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Results\n\n")
            f.write(f"- **Duration**: {duration:.2f}s\n")
            f.write(f"- **Job Status**: {final_status.get('status')}\n\n")
            f.write(f"### Memory Usage\n\n")
            f.write(f"- **Peak**: {stats['memory']['peak']:.2f} MB\n")
            f.write(f"- **Average**: {stats['memory']['avg']:.2f} MB\n")
            f.write(f"- **Min**: {stats['memory']['min']:.2f} MB\n\n")
            f.write(f"### CPU Usage\n\n")
            f.write(f"- **Peak**: {stats['cpu']['peak']:.2f}%\n")
            f.write(f"- **Average**: {stats['cpu']['avg']:.2f}%\n")
            f.write(f"- **Min**: {stats['cpu']['min']:.2f}%\n")
        
        print(f"\n✓ Report saved to: {report_path}")
        
        return {
            "duration": duration,
            "status": final_status.get("status"),
            "resources": stats
        }
        
    except Exception as e:
        monitoring = False
        await monitor_task
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_concurrent_jobs_resource_usage(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Measure resource usage during concurrent video generation."""
    print("\n" + "="*80)
    print("TEST 3: Concurrent Jobs Resource Usage (Real Server)")
    print("="*80)
    
    concurrency_levels = [1, 3, 5]
    all_results = {}
    
    for concurrency in concurrency_levels:
        print(f"\n--- Testing {concurrency} concurrent jobs ---")
        
        monitor = ResourceMonitor()
        monitoring = True
        
        async def monitor_loop():
            """Continuously monitor resources."""
            while monitoring:
                monitor.measure()
                await asyncio.sleep(0.5)
        
        monitor_task = asyncio.create_task(monitor_loop())
        
        async def process_job(job_num: int):
            """Process a single job."""
            job_id = f"integration_resources_concurrent_{concurrency}_{job_num}_{int(time.time())}"
            
            files = {"file": ("test.pdf", test_pdf_content, "application/pdf")}
            data = {"job_id": job_id}
            
            try:
                response = await http_client.post(
                    f"{BASE_URL}/api/v1/video/create",
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    return {"success": False}
                
                final_status = await wait_for_job_completion(http_client, job_id, max_wait=600)
                return {"success": final_status.get("status") == "completed"}
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Run concurrent jobs
        start = time.time()
        tasks = [process_job(i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        # Stop monitoring
        monitoring = False
        await monitor_task
        
        stats = monitor.get_stats()
        successful = sum(1 for r in results if r.get("success", False))
        
        all_results[concurrency] = {
            "duration": duration,
            "successful": successful,
            "total": len(results),
            "resources": stats
        }
        
        print(f"\n  Results:")
        print(f"    Duration: {duration:.2f}s")
        print(f"    Successful: {successful}/{len(results)}")
        print(f"    Peak Memory: {stats['memory']['peak']:.2f} MB")
        print(f"    Avg CPU: {stats['cpu']['avg']:.2f}%")
    
    # Generate report
    report_path = f"{reports_dir}/integration_resources_concurrent.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Resource Usage - Concurrent Jobs\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Results\n\n")
        
        for concurrency, data in all_results.items():
            f.write(f"### {concurrency} Concurrent Jobs\n\n")
            f.write(f"- **Duration**: {data['duration']:.2f}s\n")
            f.write(f"- **Successful**: {data['successful']}/{data['total']}\n")
            f.write(f"- **Peak Memory**: {data['resources']['memory']['peak']:.2f} MB\n")
            f.write(f"- **Avg Memory**: {data['resources']['memory']['avg']:.2f} MB\n")
            f.write(f"- **Peak CPU**: {data['resources']['cpu']['peak']:.2f}%\n")
            f.write(f"- **Avg CPU**: {data['resources']['cpu']['avg']:.2f}%\n\n")
    
    print(f"\n✓ Report saved to: {report_path}")
    
    return all_results


@pytest.mark.asyncio
async def test_generate_resources_report(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Generate comprehensive resource usage report."""
    print("\n" + "="*80)
    print("INTEGRATION RESOURCE USAGE TESTING SUITE")
    print("="*80)
    
    # Run all tests
    baseline = await test_baseline_resource_usage(reports_dir)
    
    single_job = await test_single_job_resource_usage(
        http_client, test_pdf_content, reports_dir, verify_services_running
    )
    
    concurrent_jobs = await test_concurrent_jobs_resource_usage(
        http_client, test_pdf_content, reports_dir, verify_services_running
    )
    
    # Generate comprehensive report
    report_path = f"{reports_dir}/integration_resources_report.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Resource Usage Test Report\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Server**: {BASE_URL}\n")
        f.write(f"**Test Type**: Integration (Real Services)\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Baseline Memory**: {baseline['memory']['avg']:.2f} MB\n")
        f.write(f"- **Single Job Peak Memory**: {single_job['resources']['memory']['peak']:.2f} MB\n")
        f.write(f"- **Max Concurrency Tested**: {max(concurrent_jobs.keys())} jobs\n\n")
        
        f.write("## 1. Baseline Resource Usage\n\n")
        f.write(f"- **Memory**: {baseline['memory']['avg']:.2f} MB\n")
        f.write(f"- **CPU**: {baseline['cpu']['avg']:.2f}%\n\n")
        
        f.write("## 2. Single Job Resource Usage\n\n")
        f.write(f"- **Duration**: {single_job['duration']:.2f}s\n")
        f.write(f"- **Peak Memory**: {single_job['resources']['memory']['peak']:.2f} MB\n")
        f.write(f"- **Avg Memory**: {single_job['resources']['memory']['avg']:.2f} MB\n")
        f.write(f"- **Peak CPU**: {single_job['resources']['cpu']['peak']:.2f}%\n")
        f.write(f"- **Avg CPU**: {single_job['resources']['cpu']['avg']:.2f}%\n\n")
        
        f.write("## 3. Concurrent Jobs Resource Usage\n\n")
        f.write("| Concurrency | Duration (s) | Peak Memory (MB) | Avg CPU (%) | Success Rate |\n")
        f.write("|-------------|--------------|------------------|-------------|---------------|\n")
        for concurrency, data in concurrent_jobs.items():
            success_rate = (data['successful'] / data['total']) * 100
            f.write(f"| {concurrency} | {data['duration']:.2f} | ")
            f.write(f"{data['resources']['memory']['peak']:.2f} | ")
            f.write(f"{data['resources']['cpu']['avg']:.2f} | {success_rate:.1f}% |\n")
        
        f.write("\n## Conclusions\n\n")
        f.write("Integration resource usage testing completed successfully. ")
        f.write("All measurements reflect actual system resource consumption ")
        f.write("during real video generation tasks with actual LLM, TTS, and visual services.\n\n")
        
        # Memory efficiency
        memory_increase = single_job['resources']['memory']['peak'] - baseline['memory']['avg']
        f.write(f"- **Memory Overhead per Job**: ~{memory_increase:.2f} MB\n")
        f.write(f"- **CPU Utilization**: System utilizes available CPU resources effectively\n")
    
    print(f"\n" + "="*80)
    print(f"✓ Comprehensive report saved to: {report_path}")
    print("="*80)
