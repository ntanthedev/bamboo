# Sử dụng image Python chính thức làm base image
FROM python:3.11-slim

# Đặt các biến môi trường
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Tạo thư mục làm việc
WORKDIR /app

# Cài đặt các gói hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    mime-support \
    # build-essential gcc # Có thể cần nếu pip install cần biên dịch
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt dependencies từ requirements.txt
# Đảm bảo requirements.txt tồn tại và được cập nhật
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ project code vào thư mục làm việc
# Đảm bảo .dockerignore được cấu hình đúng để loại bỏ file không cần thiết
COPY . .

# Port mà Django development server sẽ chạy bên trong container
# Mặc dù cổng host là 8010, cổng bên trong container vẫn là 8000 theo lệnh command
EXPOSE 8000

# CMD sẽ được định nghĩa trong docker-compose.yml cho từng service 