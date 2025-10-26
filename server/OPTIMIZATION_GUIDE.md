# Tối ưu hóa hệ thống Text-to-Video

## Tổng quan giải pháp

Hệ thống đã được tối ưu hóa với các giải pháp sau để giảm tải tài nguyên và cải thiện hiệu suất:

### 1. Resource Manager (`app/core/resource_manager.py`)
- **Giới hạn tài nguyên**: Kiểm soát CPU và RAM usage
- **Semaphore thông minh**: Giới hạn số job đồng thời (3), TTS (2), Visual (4)
- **Auto cleanup**: Tự động dọn dẹp khi memory > 70%
- **Health monitoring**: Theo dõi tài nguyên hệ thống

### 2. TTS Service Optimization (`app/services/tts_service.py`)
- **Connection pooling**: Sử dụng shared HTTP client thay vì tạo mới mỗi request
- **Resource-aware**: Sử dụng ResourceManager để kiểm soát concurrency
- **Better error handling**: Proper exception chaining
- **Streaming**: Download audio theo chunks để tiết kiệm memory

### 3. Memory Optimizer (`app/core/memory_optimizer.py`)
- **Temporary file management**: Tự động cleanup temp files
- **Streaming file operations**: Copy/process files theo chunks
- **Cache optimization**: Quản lý cache hiệu quả
- **Memory monitoring**: Theo dõi memory usage

### 4. Queue Manager (`app/core/queue_manager.py`)
- **Priority queue**: Jobs có priority (LOW, NORMAL, HIGH, URGENT)
- **Retry mechanism**: Tự động retry failed jobs
- **Job lifecycle**: Track jobs từ queue → processing → completed/failed
- **Resource-aware scheduling**: Chỉ start jobs khi có đủ tài nguyên

### 5. System Optimizer (`app/core/system_optimizer.py`)
- **Coordinated optimization**: Điều phối tất cả components
- **Monitoring loop**: Kiểm tra tài nguyên mỗi 30s
- **Graceful shutdown**: Cleanup resources khi shutdown
- **Status reporting**: Comprehensive system status

## Cách sử dụng

### Khởi động hệ thống tối ưu:
```python
from app.core.system_optimizer import start_optimization
await start_optimization()
```

### Kiểm tra trạng thái:
```python
from app.core.system_optimizer import get_optimization_status
status = await get_optimization_status()
print(f"CPU: {status['system_resources']['cpu_percent']}%")
print(f"Memory: {status['system_resources']['memory_percent']}%")
print(f"Queue: {status['queue_status']['queue_size']} jobs")
```

### Submit job với priority:
```python
from app.core.queue_manager import queue_manager, JobPriority
await queue_manager.submit_job_for_processing(
    job_id="job123",
    file_context=file_context,
    priority=JobPriority.HIGH,
    file_size=1024
)
```

## Lợi ích

1. **Giảm tải CPU**: Giới hạn concurrent jobs và TTS requests
2. **Tiết kiệm RAM**: Streaming operations và auto cleanup
3. **Tăng throughput**: Priority queue và resource-aware scheduling
4. **Ổn định hơn**: Better error handling và retry mechanisms
5. **Monitoring**: Real-time resource monitoring và alerting

## Cấu hình

Có thể điều chỉnh các thông số trong `ResourceLimits`:
- `max_cpu_percent`: Giới hạn CPU usage (default: 80%)
- `max_memory_percent`: Giới hạn RAM usage (default: 85%)
- `max_concurrent_jobs`: Số job đồng thời (default: 3)
- `max_concurrent_tts`: Số TTS requests đồng thời (default: 2)
- `max_concurrent_visual`: Số visual requests đồng thời (default: 4)
