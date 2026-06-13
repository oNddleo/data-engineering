Rất tốt, tôi sẽ vẽ cho bạn một sơ đồ tổng quan về **Edge Infrastructure của Atlassian** dựa trên nội dung đã phân tích. Sơ đồ này dùng ký pháp Mermaid, bạn có thể copy vào bất kỳ editor hỗ trợ (như Notion, GitHub, hoặc công cụ online) để xem trực quan.

```mermaid
flowchart TD
    subgraph "👨‍💻 Developer Experience"
        A["Developer khai báo service<br/>(qua config/code)"] --> B["Open Service Broker API<br/>(Nhận request)"]
    end

    subgraph "🏭 Provisioning Layer (Asynchronous)"
        B -->|Đẩy task| C["AWS SQS Queue"]
        C --> D["Worker (xử lý nền)"]
        D -->|Gọi AWS API| E["Tạo tài nguyên thực:<br/>- DNS<br/>- CloudFront<br/>- Load Balancer"]
        D -->|Lưu trạng thái| F["DynamoDB"]
        B -.->|Polling| F
    end

    subgraph "🧠 Control Plane (Sovereign)"
        F -->|Đọc cấu hình| G["Sovereign (FastAPI)<br/>Tổng hợp & gen config Envoy"]
        G --> H["Lưu config Envoy"]
    end

    subgraph "🛡️ Data Plane (Edge Layer)"
        H -->|xDS protocol| I["Envoy Proxy (hàng nghìn instance)"]
        I -->|Gọi đến| J["Sidecar Authentication (Rust)"]
        I -->|Gọi đến| K["Sidecar Authorization & Rate Limiting"]
        I -->|Proxy| L["Backend Microservices<br/>(Jira, Confluence, Trello...)"]
    end

    subgraph "🖥️ Immutable Infrastructure"
        M["Packer + SaltStack"] -->|Tạo| N["AMI chuẩn<br/>(Envoy + logging + monitoring)"]
        N -->|Launch template| O["Auto Scaling Group"]
        O -->|Scale| I
    end

    style A fill:#e1f5fe
    style B fill:#fff9c4
    style I fill:#ffccbc
    style L fill:#c8e6c9
```

### Giải thích luồng chính

1. **Developer** khai báo nhu cầu → **OSB API** nhận request.
2. OSB không xử lý đồng bộ mà đẩy task vào **SQS**, worker phía sau tạo tài nguyên AWS. Kết quả lưu vào **DynamoDB** (developer có thể poll để biết khi nào xong).
3. **Sovereign** (control plane) đọc cấu hình từ DynamoDB, sinh config Envoy và đẩy xuống các proxy qua giao thức **xDS** (hot reload).
4. **Envoy proxy** nhận traffic từ internet, gọi các **sidecar** (auth, rate limit) rồi mới forward đến **backend microservice** thật.
5. Toàn bộ proxy instance được tạo từ **AMI chuẩn** (Packer + SaltStack) và quản lý bởi **Auto Scaling Group** – khi hỏng, instance bị xóa và thay bằng instance mới hoàn toàn (immutable).

Bạn cần tôi giải thích thêm chi tiết một thành phần nào không? Hoặc bạn muốn export sơ đồ này sang dạng ảnh?
