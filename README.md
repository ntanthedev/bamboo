# BambooLab

**Nền tảng tạo đề thi online thông minh sử dụng AI**

BambooLab là một nền tảng giáo dục sử dụng trí tuệ nhân tạo tạo sinh để tự động hóa quá trình tạo và quản lý đề thi. Giáo viên có thể tải lên tài liệu và hệ thống sẽ tự động tạo câu hỏi trắc nghiệm với đáp án chi tiết.

---

## Mục lục

- [Tính năng](#tính-năng)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt](#cài-đặt)
  - [Cài đặt thủ công](#cài-đặt-thủ-công)
  - [Cài đặt với Docker](#cài-đặt-với-docker)
- [Cấu hình](#cấu-hình)
- [Sử dụng](#sử-dụng)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [API Endpoints](#api-endpoints)
- [Đóng góp](#đóng-góp)
- [Giấy phép](#giấy-phép)

---

## Tính năng

### Tạo đề thi tự động với AI
- Tải lên file PDF, DOCX, hoặc hình ảnh
- AI tự động phân tích và tạo câu hỏi trắc nghiệm
- Mỗi câu hỏi có 4 đáp án với giải thích chi tiết
- Phân loại độ khó: Dễ, Trung bình, Khó
- Theo dõi tiến trình xử lý theo thời gian thực

### Hệ thống làm bài kiểm tra
- Làm bài trắc nghiệm theo môn học
- Giới hạn thời gian 30 phút/bài
- 16 câu hỏi ngẫu nhiên mỗi lần thi
- Xem kết quả và giải thích sau khi nộp bài
- Lưu lịch sử làm bài

### Tra cứu điểm thi
- Tra cứu điểm thi học sinh giỏi tỉnh
- Thống kê xếp hạng theo môn học
- So sánh với điểm trung bình
- Thông tin về giải thưởng

### Quản lý người dùng
- Đăng ký tài khoản với mã mời
- Đăng nhập với tùy chọn ghi nhớ
- Trang cá nhân với lịch sử làm bài
- Phân quyền admin/staff

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| Backend | Django 5.2.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Task Queue | Celery 5.5.0 |
| Message Broker | Redis 7 |
| AI | Google Generative AI (Gemini 2.0 Flash) |
| Frontend | HTML, CSS, JavaScript |
| Containerization | Docker, Docker Compose |

---

## Yêu cầu hệ thống

- Python 3.10+
- Redis Server
- Docker và Docker Compose (tùy chọn)
- Google AI API Key

---

## Cài đặt

### Cài đặt thủ công

1. **Clone repository**

```bash
git clone https://github.com/ntanthedev/bamboo.git
cd bamboo
```

2. **Tạo môi trường ảo**

```bash
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

3. **Cài đặt dependencies**

```bash
pip install -r requirements.txt
```

4. **Cấu hình biến môi trường**

Tạo file `.env` tại thư mục gốc:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
GEMINI_API_KEY=your-google-ai-api-key
```

5. **Chạy migrations**

```bash
python src/manage.py migrate
```

6. **Tạo tài khoản admin**

```bash
python src/manage.py createsuperuser
```

7. **Khởi chạy server**

```bash
# Terminal 1: Django server
python src/manage.py runserver

# Terminal 2: Celery worker
cd src
celery -A bamboolab worker --loglevel=info
```

Truy cập ứng dụng tại: http://localhost:8000

### Cài đặt với Docker

1. **Clone repository**

```bash
git clone https://github.com/ntanthedev/bamboo.git
cd bamboo
```

2. **Cấu hình biến môi trường**

Tạo file `.env`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
GEMINI_API_KEY=your-google-ai-api-key
POSTGRES_DB=bamboolab
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
```

3. **Build và khởi chạy**

```bash
docker-compose up --build
```

4. **Chạy migrations (trong container)**

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

Truy cập ứng dụng tại: http://localhost:8010

---

## Cấu hình

### Biến môi trường

| Biến | Mô tả | Bắt buộc |
|------|-------|----------|
| `SECRET_KEY` | Django secret key | Có |
| `DEBUG` | Chế độ debug (True/False) | Có |
| `GEMINI_API_KEY` | Google AI API key | Có |
| `POSTGRES_DB` | Tên database PostgreSQL | Docker |
| `POSTGRES_USER` | User PostgreSQL | Docker |
| `POSTGRES_PASSWORD` | Password PostgreSQL | Docker |

### Ports

| Service | Port nội bộ | Port host |
|---------|------------|-----------|
| Django | 8000 | 8010 |
| PostgreSQL | 5452 | 5452 |
| Redis | 6379 | 7812 |

---

## Sử dụng

### Đối với giáo viên (Staff)

1. Đăng nhập với tài khoản staff
2. Vào **Upload Document** để tải lên tài liệu
3. Chọn môn học và điền các thông tin cần thiết
4. Chờ hệ thống xử lý và tạo câu hỏi tự động
5. Xem và quản lý câu hỏi trong **Documents**

### Đối với học sinh

1. Đăng ký tài khoản với mã mời
2. Vào **Quiz** để chọn môn học
3. Bắt đầu làm bài và hoàn thành trong 30 phút
4. Xem kết quả và giải thích chi tiết
5. Theo dõi lịch sử làm bài trong **Profile**

### Tra cứu điểm

1. Vào **Tra điểm**
2. Nhập số báo danh
3. Chọn kỳ thi (Lớp 10 hoặc Lớp 11)
4. Xem kết quả và thống kê

---

## Cấu trúc dự án

```
bamboo/
├── src/
│   ├── bamboolab/          # Django project config
│   │   ├── settings.py     # Cấu hình Django
│   │   ├── urls.py         # URL routing
│   │   ├── celery.py       # Cấu hình Celery
│   │   └── wsgi.py         # WSGI entry
│   ├── core/               # Ứng dụng chính
│   │   ├── models.py       # Database models
│   │   ├── views.py        # View functions
│   │   ├── forms.py        # Django forms
│   │   ├── tasks.py        # Celery tasks
│   │   └── migrations/     # Database migrations
│   ├── templates/          # HTML templates
│   ├── static/             # CSS, JS, images
│   ├── data/               # CSV data files
│   └── manage.py           # Django CLI
├── requirements.txt        # Python packages
├── Dockerfile              # Docker config
├── docker-compose.yml      # Docker Compose
└── README.md
```

---

## API Endpoints

### Trang chính

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Trang chủ |
| GET | `/admin/` | Django Admin |

### Xác thực

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET/POST | `/login/` | Đăng nhập |
| GET | `/logout/` | Đăng xuất |
| GET/POST | `/register/` | Đăng ký |
| GET | `/profile/` | Trang cá nhân |

### Quiz

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/quiz/` | Danh sách môn học |
| GET | `/quiz/start/<subject_id>/` | Bắt đầu làm bài |
| GET | `/quiz/attempt/<attempt_id>/` | Làm bài |
| POST | `/quiz/submit/<attempt_id>/` | Nộp bài |
| GET | `/quiz/result/<attempt_id>/` | Xem kết quả |

### Tài liệu

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET/POST | `/upload-document/` | Upload tài liệu |
| GET | `/documents/` | Danh sách tài liệu |
| GET | `/document-status/<id>/` | Trạng thái xử lý |
| GET | `/api/document-status/<id>/` | API trạng thái |

### Tra điểm

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET/POST | `/score-ranking/` | Tra cứu điểm |
| GET | `/import-csv/` | Import dữ liệu CSV |

---

## Đóng góp

Chúng tôi chào đón mọi đóng góp từ cộng đồng!

### Quy trình đóng góp

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

### Báo lỗi

Nếu phát hiện lỗi, vui lòng tạo issue với các thông tin:

- Mô tả lỗi chi tiết
- Các bước tái tạo lỗi
- Screenshots (nếu có)
- Môi trường (OS, Python version, etc.)

---

## Giấy phép

Dự án này được cấp phép dưới giấy phép MIT. Xem chi tiết tại file [LICENSE](LICENSE).
