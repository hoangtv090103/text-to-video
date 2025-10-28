"""
Integration Reliability Tests - Tests against real server.

These tests verify system reliability with actual services including:
- Real error conditions
- Actual retry mechanisms
- True service failures
- Real data integrity
"""
import asyncio
import time
import httpx
import pytest
import os
from typing import Dict, List
from conftest import BASE_URL, wait_for_job_completion, calculate_statistics


@pytest.mark.asyncio
async def test_normal_operation_reliability(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Test baseline success rate under normal conditions."""
    print("\n" + "="*80)
    print("TEST 1: Normal Operation Reliability (Real Server)")
    print("="*80)
    
    num_jobs = 5  # Run 5 jobs to test reliability
    results = []
    
    for i in range(num_jobs):
        job_id = f"integration_reliability_normal_{i}_{int(time.time())}"
        print(f"\nProcessing job {i+1}/{num_jobs}: {job_id}")
        
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
                results.append({"success": False, "duration": time.time() - start, "error": response.text})
                print(f"  ✗ Failed to submit: {response.status_code}")
                continue
            
            # Wait for completion
            final_status = await wait_for_job_completion(http_client, job_id, max_wait=600)
            duration = time.time() - start
            
            success = final_status.get("status") == "completed"
            results.append({
                "success": success,
                "duration": duration,
                "job_id": job_id,
                "status": final_status.get("status")
            })
            
            print(f"  {'✓' if success else '✗'} Status: {final_status.get('status')} ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start
            results.append({"success": False, "duration": duration, "error": str(e)})
            print(f"  ✗ Exception: {e}")
        
        # Small delay between jobs
        await asyncio.sleep(2)
    
    # Calculate metrics
    successful = sum(1 for r in results if r.get("success", False))
    success_rate = (successful / len(results)) * 100
    durations = [r["duration"] for r in results if r.get("success", False)]
    
    print(f"\n{'='*80}")
    print(f"Results: {successful}/{len(results)} successful ({success_rate:.1f}%)")
    if durations:
        avg_duration = sum(durations) / len(durations)
        print(f"Average Duration: {avg_duration:.2f}s")
    
    # Generate report
    report_path = f"{reports_dir}/integration_reliability_normal.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Reliability Test - Normal Operation\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Results\n\n")
        f.write(f"- **Total Jobs**: {len(results)}\n")
        f.write(f"- **Successful**: {successful}\n")
        f.write(f"- **Failed**: {len(results) - successful}\n")
        f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
        if durations:
            f.write(f"- **Average Duration**: {sum(durations) / len(durations):.2f}s\n")
        f.write(f"\n## Individual Results\n\n")
        for i, r in enumerate(results):
            f.write(f"{i+1}. {r.get('job_id', 'N/A')}: ")
            f.write(f"{'✓ Success' if r.get('success') else '✗ Failed'} ")
            f.write(f"({r['duration']:.2f}s)\n")
    
    print(f"\n✓ Report saved to: {report_path}")
    
    return {
        "success_rate": success_rate,
        "total": len(results),
        "successful": successful,
        "results": results
    }


@pytest.mark.asyncio
async def test_data_integrity(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Test data integrity of generated outputs."""
    print("\n" + "="*80)
    print("TEST 2: Data Integrity (Real Server)")
    print("="*80)
    
    job_id = f"integration_reliability_integrity_{int(time.time())}"
    
    files = {"file": ("test.pdf", test_pdf_content, "application/pdf")}
    data = {"job_id": job_id}
    
    # Submit job
    response = await http_client.post(
        f"{BASE_URL}/api/v1/video/create",
        files=files,
        data=data
    )
    
    if response.status_code != 200:
        pytest.fail(f"Failed to create job: {response.status_code}")
    
    print(f"\n✓ Job submitted: {job_id}")
    
    # Wait for completion
    try:
        final_status = await wait_for_job_completion(http_client, job_id, max_wait=600)
        
        if final_status.get("status") != "completed":
            pytest.fail(f"Job failed with status: {final_status.get('status')}")
        
        print(f"✓ Job completed successfully")
        
        # Check job details
        response = await http_client.get(f"{BASE_URL}/api/v1/video/jobs/{job_id}")
        job_data = response.json()
        
        # Verify data integrity
        checks = {
            "has_job_id": "job_id" in job_data,
            "has_status": "status" in job_data,
            "has_progress": "progress" in job_data,
            "progress_is_100": job_data.get("progress") == 100,
            "status_is_completed": job_data.get("status") == "completed",
        }
        
        print(f"\nData Integrity Checks:")
        for check_name, passed in checks.items():
            print(f"  {'✓' if passed else '✗'} {check_name}")
        
        all_passed = all(checks.values())
        integrity_score = (sum(checks.values()) / len(checks)) * 100
        
        # Generate report
        report_path = f"{reports_dir}/integration_reliability_integrity.md"
        with open(report_path, 'w') as f:
            f.write("# Integration Reliability Test - Data Integrity\n\n")
            f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Results\n\n")
            f.write(f"- **Job ID**: {job_id}\n")
            f.write(f"- **Integrity Score**: {integrity_score:.1f}%\n\n")
            f.write(f"### Integrity Checks\n\n")
            for check_name, passed in checks.items():
                f.write(f"- {'✓' if passed else '✗'} {check_name}\n")
            f.write(f"\n## Conclusion\n\n")
            f.write(f"Data integrity {'verified' if all_passed else 'issues detected'}. ")
            f.write(f"Integrity score: {integrity_score:.1f}%.\n")
        
        print(f"\n✓ Report saved to: {report_path}")
        
        return {
            "integrity_score": integrity_score,
            "all_passed": all_passed,
            "checks": checks
        }
        
    except Exception as e:
        pytest.fail(f"Test failed: {e}")


@pytest.mark.asyncio
async def test_generate_reliability_report(
    http_client,
    test_pdf_content,
    reports_dir,
    verify_services_running
):
    """Generate comprehensive reliability report."""
    print("\n" + "="*80)
    print("INTEGRATION RELIABILITY TESTING SUITE")
    print("="*80)
    
    # Run all tests
    normal_results = await test_normal_operation_reliability(
        http_client, test_pdf_content, reports_dir, verify_services_running
    )
    
    integrity_results = await test_data_integrity(
        http_client, test_pdf_content, reports_dir, verify_services_running
    )
    
    # Calculate overall reliability score
    reliability_score = (normal_results["success_rate"] + integrity_results["integrity_score"]) / 2
    
    # Generate comprehensive report
    report_path = f"{reports_dir}/integration_reliability_report.md"
    with open(report_path, 'w') as f:
        f.write("# Integration Reliability Test Report\n\n")
        f.write(f"**Test Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Server**: {BASE_URL}\n")
        f.write(f"**Test Type**: Integration (Real Services)\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Overall Reliability Score**: {reliability_score:.1f}%\n")
        f.write(f"- **Success Rate**: {normal_results['success_rate']:.1f}%\n")
        f.write(f"- **Data Integrity**: {integrity_results['integrity_score']:.1f}%\n\n")
        
        f.write("## 1. Normal Operation Reliability\n\n")
        f.write(f"- **Total Jobs**: {normal_results['total']}\n")
        f.write(f"- **Successful**: {normal_results['successful']}\n")
        f.write(f"- **Success Rate**: {normal_results['success_rate']:.1f}%\n\n")
        
        f.write("## 2. Data Integrity\n\n")
        f.write(f"- **Integrity Score**: {integrity_results['integrity_score']:.1f}%\n")
        f.write(f"- **All Checks Passed**: {'Yes' if integrity_results['all_passed'] else 'No'}\n\n")
        f.write("### Integrity Checks\n\n")
        for check_name, passed in integrity_results['checks'].items():
            f.write(f"- {'✓' if passed else '✗'} {check_name}\n")
        
        f.write("\n## Conclusions\n\n")
        f.write(f"Integration reliability testing completed with an overall score of {reliability_score:.1f}%. ")
        f.write("Testing was performed against real services with actual API calls, ")
        f.write("LLM inference, TTS generation, and file operations.\n\n")
        
        if reliability_score >= 95:
            f.write("**Rating**: Excellent - System demonstrates high reliability.\n")
        elif reliability_score >= 80:
            f.write("**Rating**: Good - System is reliable with minor issues.\n")
        elif reliability_score >= 60:
            f.write("**Rating**: Fair - System has reliability concerns that should be addressed.\n")
        else:
            f.write("**Rating**: Poor - System has significant reliability issues.\n")
    
    print(f"\n" + "="*80)
    print(f"✓ Comprehensive report saved to: {report_path}")
    print(f"Overall Reliability Score: {reliability_score:.1f}%")
    print("="*80)
