# TODO List
## Dịch vụ tạo video từ văn bản
---

## 🚀 PHẦN I: HOÀN THIỆN ỨNG DỤNG

### 1. Xử lý lỗi & kiểm tra dữ liệu

#### 1.1 Cải thiện xử lý ngoại lệ
- **File**: `app/main.py`
  - [ ] Thêm cơ chế ngắt kết nối tạm thời khi gọi tới các dịch vụ bên ngoài bị lỗi liên tục (giúp hệ thống không bị quá tải khi dịch vụ bên ngoài gặp sự cố)
  - [ ] Thêm kiểm tra cho việc tải lên tập tin (kích thước, định dạng, loại nội dung)
  - [ ] Xử lý trường hợp dịch vụ Redis không hoạt động

#### 1.2 Kiểm tra dữ liệu đầu vào
- **File**: `app/schemas/video.py`
  - [ ] Tạo mẫu kiểm tra dữ liệu cho yêu cầu gửi lên
  - [ ] Kiểm tra định dạng tập tin được hỗ trợ (txt, pdf, md)
  - [ ] Thêm giới hạn kích thước và kiểm tra nội dung tập tin
  - [ ] Kiểm tra định dạng mã công việc trong các điểm truy cập API

### 2. Bổ sung tính năng còn thiếu

#### 2.1 Dịch vụ ghép video
- **File**: `app/services/video_composer_sync.py`
  - [ ] Hoàn thiện logic tạo video
  - [ ] Đảm bảo đồng bộ âm thanh và hình ảnh

#### 2.2 Quản lý tập tin
- **File**: `app/utils/file.py`
  - [ ] Thêm chức năng dọn dẹp tập tin

#### 2.3 Quản lý công việc
- **Files**: `app/orchestrator.py`, `app/services/redis_service.py`
  - [ ] Thêm chức năng hủy công việc
  - [ ] Thêm cơ chế thử lại công việc với thời gian chờ tăng dần
  - [ ] Thêm hàng đợi công việc theo mức độ ưu tiên
  - [ ] Thêm chức năng expiration job và clean job
  - [ ] Thêm chức năng lưu kết quả công việc

## ⚡ PHẦN II: CẢI THIỆN HIỆU NĂNG

### 1. Tối ưu hiệu năng nhập/xuất

#### 1.1 Tối ưu kết nối HTTP
- **Files**: `app/services/tts_service.py`, `app/services/llm_service.py`
  - [ ] **Quan trọng**: Thêm chức năng tái sử dụng kết nối cho httpx
  - [ ] Tối ưu thời gian chờ (hiện tại TTS chờ 300s quá lâu)

#### 1.2 Tối ưu nhập/xuất tập tin
- **Files**: `app/services/tts_service.py`, `app/services/visual_services.py`
  #### 1.2 Tối ưu nhập/xuất tập tin

  - [ ] **Ưu tiên cao**: Thực hiện thao tác tập tin bất đồng bộ
    - [ ] Sử dụng truyền tải liên tục để xử lý tập tin lớn khi tải lên/xuống
    - [ ] Nén tập tin khi lưu để tiết kiệm dung lượng
    - [ ] Thêm chức năng tự động dọn dẹp tập tin tạm

### 2. Quản lý bộ nhớ

#### 2.1 Tối ưu sử dụng bộ nhớ
- **Files**: Tất cả các file dịch vụ
  - [ ] **Quan trọng**: Xử lý tập tin tiết kiệm bộ nhớ
  - [ ] Sử dụng bộ sinh thay vì tải toàn bộ tập tin vào bộ nhớ
  - [ ] Thêm chức năng giám sát và giới hạn bộ nhớ
  - [ ] Tối ưu hóa thu gom bộ nhớ

#### 2.2 Quản lý tài nguyên
- **File**: `app/services/redis_service.py`
  - [ ] Thêm chức năng tái sử dụng kết nối Redis
  - [ ] Thêm kiểm tra sức khỏe kết nối
  - [ ] Tối ưu thời gian sống của khóa Redis
  - [ ] Thêm hỗ trợ cụm Redis để mở rộng

### 3. Tối ưu xử lý song song

#### 3.1 Tăng cường xử lý bất đồng bộ
- **File**: `app/orchestrator.py`
  - [ ] **Ưu tiên cao**: Tối ưu thuật toán lên lịch công việc
  - [ ] Thêm chức năng hủy công việc đúng cách
  - [ ] Thêm chức năng ưu tiên động cho công việc
  - [ ] Sử dụng asyncio.Semaphore để giới hạn số công việc chạy đồng thời

#### 3.2 Xử lý background job
- **File**: `app/main.py`
  - [ ] Thêm chức năng quản lý công việc nền đúng cách
  - [ ] Thêm hàng đợi công việc theo mức độ ưu tiên
  - [ ] Thêm chức năng mở rộng worker pool xử lý công việc
  <!-- - [ ] Thêm chức năng gửi job status về cho người dùng -->

### 4. Chiến lược lưu tạm

#### 4.1 Lưu tạm ở cấp ứng dụng
- **Tất cả các file dịch vụ**
  - [ ] **Ưu tiên cao**: Lưu tạm kết quả LLM cho input giống nhau
  - [ ] Thêm chức năng lưu tạm âm thanh TTS
  - [ ] Lưu tạm các tài nguyên hình ảnh đã tạo
  - [ ] Thêm cơ chế xóa dữ liệu lưu tạm

#### 4.2 Tối ưu Redis
- **File**: `app/services/redis_service.py`
  - [ ] Tối ưu cách sử dụng cấu trúc dữ liệu Redis
  - [ ] Thêm hỗ trợ cụm Redis để tăng độ sẵn sàng
  - [ ] Tối ưu bộ nhớ Redis
  - [ ] Thêm chức năng làm nóng bộ nhớ đệm

### 5. Tối ưu lưu trữ dữ liệu

<!-- #### 5.1 Tối ưu truy cập dữ liệu
- [ ] Thêm chức năng tái sử dụng kết nối cơ sở dữ liệu (nếu có)
- [ ] Tối ưu truy vấn và cấu trúc dữ liệu Redis
- [ ] Thêm chức năng đọc bản sao để mở rộng

#### 5.2 Tối ưu lưu trữ tài nguyên
- **Files**: `app/services/tts_service.py`, `app/services/visual_services.py`
  - [ ] **Quan trọng**: Chuyển lưu trữ từ `/tmp` sang nơi lưu trữ lâu dài
  - [ ] Thêm chức năng tích hợp CDN để phân phối tài nguyên
  - [ ] Thêm chức năng nén và tối ưu tài nguyên
  - [ ] Thêm chức năng lưu trữ tập tin phân tán -->

### 6. Tối ưu hiệu năng API

#### 6.1 Tối ưu xử lý yêu cầu
- **File**: `app/main.py`
  - [ ] Thêm chức năng nén dữ liệu gửi/nhận
  - [ ] Thêm chức năng lưu tạm phản hồi API
  - [ ] Tối ưu hóa chuyển đổi dữ liệu
  - [ ] Thêm chức năng giới hạn tốc độ truy cập API hiệu quả

#### 6.2 Xử lý đồng thời yêu cầu
- [ ] **Quan trọng**: Thêm chức năng giới hạn kết nối đúng cách
- [ ] Thêm hàng đợi yêu cầu
- [ ] Tối ưu cấu hình worker của FastAPI
- [ ] Chuẩn bị cho việc cân bằng tải

---

## 🔧 VIỆC CẦN LÀM

### Vấn đề nghiêm trọng cần sửa ngay:
- [x] Sửa giá trị thời gian hard-code trong health check ở `app/main.py` (dùng thời gian thực/uptime)
- [x] Giảm timeout TTS trong `app/services/tts_service.py` (ví dụ ~60s; tách connect/read timeout theo request)
- [ ] Bật tái sử dụng kết nối HTTP (httpx.Client + connection pooling) cho `app/services/tts_service.py` và `app/services/llm_service.py`
- [ ] Tái sử dụng kết nối Redis + health check trong `app/services/redis_service.py`
- [ ] Thêm xác thực input upload file ở `app/schemas/video.py` và API: định dạng (txt/pdf/md), kích thước, content-type, job_id hợp lệ
- [ ] Chuẩn hóa xử lý ngoại lệ trong `app/main.py` và các service (bắt lỗi cụ thể, mã lỗi/ thông điệp rõ ràng)
- [ ] Dọn dẹp/làm mới chiến lược lưu tạm: tránh phụ thuộc `/tmp` cho dữ liệu cần tồn tại lâu hơn vòng đời process

### Các điểm nghẽn hiệu năng cần giải quyết:
- [ ] Chuyển thao tác tập tin sang bất đồng bộ; hỗ trợ streaming upload/download trong `app/services/tts_service.py`, `app/services/visual_services.py`
- [ ] Thêm cache ngắn hạn: kết quả LLM theo input giống nhau, âm thanh TTS, tài nguyên hình ảnh đã tạo
- [ ] Giới hạn số công việc đồng thời bằng `asyncio.Semaphore` trong `app/orchestrator.py` và hỗ trợ hủy job đúng cách
- [ ] Thêm retry với backoff tăng dần và hàng đợi ưu tiên trong `app/orchestrator.py`, `app/services/redis_service.py`
- [ ] Tối ưu tầng API: giới hạn kết nối đồng thời, bật nén phản hồi, cân nhắc response caching nhẹ trong `app/main.py`

---

## 🚀 LƯU Ý KHI TRIỂN KHAI

### Sẵn sàng cho môi trường thực tế:
- [ ] Thêm chức năng quản lý cấu hình đúng cách
- [ ] Tối ưu hóa đóng gói ứng dụng
- [ ] Thêm điểm kiểm tra sức khỏe
- [ ] Thêm chức năng giám sát và cảnh báo
- [ ] Thêm chức năng tổng hợp nhật ký
- [ ] Thêm chức năng sao lưu và phục hồi dữ liệu
- [ ] Tăng cường bảo mật
- [ ] Thêm chức năng giám sát hiệu năng
