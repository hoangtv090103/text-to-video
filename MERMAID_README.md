# 🧜‍♀️ Mermaid Diagram Integration

Ứng dụng text-to-video hiện hỗ trợ tạo diagram từ Mermaid syntax với cách tiếp cận Python-native sử dụng thư viện `mermaid-py`.

## ✨ Tính năng mới

### 🚀 Python-native Integration
- **mermaid-py**: Thư viện Python thuần túy, không cần Node.js
- **Tự động fallback**: Nhiều cấp độ fallback để đảm bảo luôn tạo được output
- **Hiệu suất cao**: Xử lý local, không phụ thuộc external service

### 📦 Cài đặt tự động
```bash
# Tự động cài đặt khi chạy server
pip install mermaid-py cairosvg
```

### 🔄 Multi-level Fallback System
1. **mermaid-py + cairosvg**: Render SVG → PNG (tốt nhất)
2. **mermaid-py + online service**: Sử dụng mermaid.ink
3. **Text-based fallback**: Hiển thị syntax với highlighting

## 📝 Sử dụng trong Prompts

```markdown
Hãy tạo một diagram luồng xử lý dữ liệu:

```
graph TD
    A[Input Data] --> B[Processing]
    B --> C[Database]
    C --> D[Output]
    D --> E[User Display]
```

Hoặc sử dụng flowchart:

```
flowchart LR
    A[Start] --> B{Is Valid?}
    B -->|Yes| C[Process Data]
    B -->|No| D[Show Error]
    C --> E[End]
    D --> E
```
```

## 🔧 Cách hoạt động:

1. **Input**: Mermaid code trong visual prompt
2. **Processing**: Sử dụng mermaid-py để render
3. **Conversion**: SVG → PNG với cairosvg
4. **Fallback**: Online service hoặc text representation
5. **Output**: PNG file với diagram chất lượng cao

## 📝 Ví dụ Visual Prompts:

```text
visual_prompt: "Create a flowchart showing the data processing pipeline"
```

```text
visual_prompt: "Generate a diagram with the formula: graph TD; A-->B; B-->C;"
```

## 🎯 Lợi ích:

- 🎨 **Visual đẹp**: Diagram chất lượng cao từ thư viện chính thức
- 🔄 **Fallback mạnh**: 3 cấp độ fallback đảm bảo 100% success rate
- 📦 **Không dependency**: Không cần Node.js, chỉ Python packages
- ⚡ **Hiệu suất**: Xử lý local nhanh hơn CLI
- 🔧 **Dễ maintain**: Pure Python, dễ debug và customize

## 🌐 Environment Variables

```bash
# Custom mermaid.ink server (optional)
MERMAID_INK_SERVER=https://your-custom-server.com
```

## 🐛 Troubleshooting:

- Nếu bị lỗi import mermaid-py → Chạy `pip install mermaid-py`
- Nếu bị lỗi cairosvg → Chạy `pip install cairosvg`
- Nếu diagram không đẹp → Kiểm tra Mermaid syntax
- Nếu fallback text hiển thị → mermaid-py hoạt động nhưng thiếu cairosvg

## 📊 So sánh với cách cũ:

| Aspect | CLI (cũ) | Python (mới) |
|--------|----------|--------------|
| **Setup** | Node.js + npm | Pure Python |
| **Performance** | Tốt | Tốt hơn |
| **Dependencies** | External CLI | Python packages |
| **Maintenance** | Khó | Dễ |
| **Customization** | Giới hạn | Linh hoạt |
| **Fallback** | Text only | Multi-level |
