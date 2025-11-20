# BambooLab - Nền tảng tạo đề thi online thông minh

BambooLab là một nền tảng giáo dục đột phá, sử dụng trí tuệ nhân tạo (AI) để tự động hóa quá trình tạo và quản lý đề thi. Với BambooLab, giáo viên và các tổ chức giáo dục có thể dễ dàng chuyển đổi các đề thi giấy truyền thống thành các bài kiểm tra online, tạo đáp án chi tiết và sinh ra các bộ đề ngẫu nhiên một cách nhanh chóng và hiệu quả.

## Tính năng nổi bật

- **Tạo đề thi từ file**: Tải lên các file đề thi (định dạng PDF, DOCX, hoặc ảnh) và hệ thống AI sẽ tự động phân tích, bóc tách câu hỏi và các lựa chọn để tạo thành một bài kiểm tra online hoàn chỉnh.
- **Tạo đáp án tự động**: AI sẽ phân tích nội dung câu hỏi và đưa ra đáp án chính xác, giúp tiết kiệm thời gian và công sức cho giáo viên.
- **Sinh đề ngẫu nhiên**: Từ một ngân hàng câu hỏi có sẵn, hệ thống có thể tạo ra vô số các bộ đề thi khác nhau, đảm bảo tính khách quan và công bằng trong kiểm tra.
- **Quản lý ngân hàng câu hỏi**: Dễ dàng quản lý, chỉnh sửa và phân loại các câu hỏi theo chủ đề, độ khó.
- **Giao diện thân thiện**: Giao diện người dùng được thiết kế đơn giản, trực quan, giúp người dùng dễ dàng thao tác và sử dụng.
- **Thống kê và báo cáo**: Cung cấp các báo cáo chi tiết về kết quả của học sinh, giúp giáo viên nắm bắt được tình hình học tập và đưa ra các phương pháp giảng dạy phù hợp.

## Công nghệ sử dụng

- **Backend**: Django, Django REST Framework
- **Frontend**: HTML, CSS, JavaScript
- **Cơ sở dữ liệu**: PostgreSQL (production), SQLite (development)
- **Xử lý bất đồng bộ**: Celery, Redis
- **AI & Machine Learning**: Google Generative AI
- **Deployment**: Docker

## Cài đặt và triển khai

### Yêu cầu hệ thống

- Python 3.10+
- Docker và Docker Compose

### Hướng dẫn cài đặt

1.  **Clone repository:**

    ```bash
    git clone https://github.com/ntanthedev/bamboo.git
    cd bamboolab
    ```

2.  **Tạo và kích hoạt môi trường ảo:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # Trên Windows dùng `venv\Scripts\activate`
    ```

3.  **Cài đặt các thư viện cần thiết:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình biến môi trường:**

    Tạo file `.env` ở thư mục gốc và thêm các biến môi trường cần thiết (ví dụ: `SECRET_KEY`, `DATABASE_URL`, `GOOGLE_API_KEY`).

5.  **Chạy migrate cơ sở dữ liệu:**

    ```bash
    python src/manage.py migrate
    ```

6.  **Khởi chạy server:**

    ```bash
    python src/manage.py runserver
    ```

### Triển khai với Docker

1.  **Build và khởi chạy các container:**

    ```bash
    docker-compose up --build
    ```

## Hướng dẫn sử dụng

1.  Truy cập vào trang chủ.
2.  Đăng ký/Đăng nhập vào tài khoản.
3.  Vào mục "Tạo đề thi" và tải lên file đề thi của bạn.
4.  Hệ thống sẽ xử lý và tạo ra một bài kiểm tra online.
5.  Bạn có thể xem lại, chỉnh sửa và chia sẻ bài kiểm tra cho học sinh.

## Đóng góp

Chúng tôi luôn chào đón các đóng góp từ cộng đồng. Nếu bạn có bất kỳ ý tưởng, đề xuất hoặc muốn báo lỗi, vui lòng tạo một "Issue" hoặc "Pull Request" trên repository này.

## Giấy phép

Dự án này được cấp phép dưới giấy phép MIT. Xem chi tiết tại file [LICENSE](LICENSE).