# CLAUDE.md - BambooLab Project Guide

## Project Overview

BambooLab is an AI-powered online exam creation platform for educators. It allows teachers to upload documents (PDF, images, DOCX) and automatically generates multiple-choice questions using Google's Gemini AI. The platform also includes student score ranking lookup and quiz management features.

## Tech Stack

- **Backend**: Django 5.2.0
- **Database**: SQLite (development), PostgreSQL (production)
- **Task Queue**: Celery 5.5.0 with Redis
- **AI**: Google Generative AI (Gemini 2.0 Flash)
- **Deployment**: Docker, Docker Compose
- **Python**: 3.11+

## Project Structure

```
bamboo/
├── src/                          # Source code directory
│   ├── bamboolab/               # Django project configuration
│   │   ├── settings.py          # Django settings
│   │   ├── urls.py              # Main URL configuration
│   │   ├── celery.py            # Celery configuration
│   │   ├── wsgi.py              # WSGI entry point
│   │   └── asgi.py              # ASGI entry point
│   ├── core/                    # Main application
│   │   ├── models.py            # Database models
│   │   ├── views.py             # View functions
│   │   ├── forms.py             # Django forms
│   │   ├── tasks.py             # Celery tasks (AI processing)
│   │   ├── admin.py             # Admin configuration
│   │   ├── signals.py           # Django signals
│   │   ├── migrations/          # Database migrations
│   │   ├── templatetags/        # Custom template tags
│   │   └── management/commands/ # Custom management commands
│   ├── templates/               # HTML templates
│   ├── static/                  # Static files (CSS, images)
│   ├── data/                    # CSV data files for score ranking
│   └── manage.py                # Django management script
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker build configuration
├── docker-compose.yml           # Docker Compose services
└── README.md                    # Project documentation
```

## Key Models

Located in `src/core/models.py`:

- **Subject** - Academic subjects (e.g., Math, Physics)
- **Question** - Quiz questions with difficulty levels (easy/medium/hard)
- **Answer** - Answer choices for questions with explanations
- **Document** - Uploaded documents for AI processing
- **UploadedFile** - Individual files linked to documents
- **Candidate** - Student exam score records
- **QuizAttempt** - User quiz session tracking
- **UserAnswer** - User's selected answers in quiz attempts
- **UserProfile** - Extended user information
- **InviteCode** - Registration invite codes with usage limits

## Main Features

### 1. Score Ranking (tra-diem)
- Lookup student exam scores by ID number
- Displays rankings, statistics, and prize information
- Imports data from CSV files (`src/data/data1.csv`, `src/data/data2.csv`)

### 2. Quiz System
- Browse quizzes by subject at `/quiz/`
- Take timed quizzes (30 minutes, 16 questions)
- View results with explanations
- Track quiz history in user profile

### 3. Document Processing (AI)
- Upload documents at `/upload-document/` (staff only)
- Supports PDF, images, DOCX
- Celery task processes files via Gemini API
- Auto-generates questions with answers and explanations
- Real-time progress tracking

### 4. User Authentication
- Registration with invite codes
- Login with remember me option
- User profiles with quiz history

## Development Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python src/manage.py migrate

# Start development server
python src/manage.py runserver

# Start Celery worker (separate terminal)
celery -A bamboolab worker --loglevel=info
```

### Docker Development

```bash
# Build and start all services
docker-compose up --build

# Services will be available at:
# - Web: http://localhost:8010
# - PostgreSQL: localhost:5452
# - Redis: localhost:7812
```

### Database Operations

```bash
# Create new migrations
python src/manage.py makemigrations

# Apply migrations
python src/manage.py migrate

# Create superuser
python src/manage.py createsuperuser

# Migrate subjects (custom command)
python src/manage.py migrate_subjects
```

## Environment Variables

Required in `.env` file:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
GEMINI_API_KEY=your-google-ai-api-key

# For Docker/Production PostgreSQL
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
```

## URL Routes

Main routes defined in `src/bamboolab/urls.py`:

| Path | Name | Description |
|------|------|-------------|
| `/` | home | Home page |
| `/admin/` | admin | Django admin |
| `/score-ranking/` | score-ranking | Score lookup |
| `/quiz/` | quiz-list | Quiz subject list |
| `/quiz/start/<subject_id>/` | start_quiz | Start new quiz |
| `/quiz/attempt/<attempt_id>/` | take_quiz | Take quiz |
| `/quiz/result/<attempt_id>/` | quiz_result | View results |
| `/upload-document/` | upload-document | Upload docs (staff) |
| `/documents/` | document-list | List documents |
| `/login/` | login_view | User login |
| `/register/` | register_view | User registration |
| `/profile/` | user_profile | User profile |

## Code Conventions

### Python/Django

- Vietnamese language used for UI strings and comments
- Function-based views (no class-based views)
- Model verbose names in Vietnamese
- Use `get_object_or_404()` for retrieving objects
- Apply `@login_required` decorator for authenticated views
- Apply `@user_passes_test(lambda u: u.is_staff)` for staff-only views
- Use Django's `messages` framework for user feedback

### Templates

- Base template: `src/templates/base.html`
- Templates use Django template language
- Static files referenced with `{% static %}` tag
- Custom template tags in `src/core/templatetags/custom_tags.py`

### Forms

- Custom forms extend Django's built-in forms
- Use Bootstrap-compatible CSS classes
- Form validation with custom `clean_*` methods

### Celery Tasks

- Tasks defined in `src/core/tasks.py`
- Use `@shared_task` decorator
- Handle progress tracking via model updates
- Clean up temporary files (Google File API) in `finally` block
- Log operations with Python's logging module

## AI Integration

The document processing uses Google's Gemini API:

1. Files uploaded to Google File API
2. Gemini 2.0 Flash model processes content
3. Returns JSON array of questions with:
   - Question text
   - 4 answer choices
   - Correct answer flag
   - Difficulty level
   - Explanations

### Prompt Requirements

- Request JSON-only response (no markdown)
- Each question has exactly 4 answers
- One correct answer per question
- Include explanations for all answers

## Security Notes

- CSRF protection enabled
- `ALLOWED_HOSTS` configured for production domain
- Sensitive keys should be in `.env` (not committed)
- Staff-only views for document uploads
- Password validation enabled

## Testing

Currently no automated tests. When adding tests:

- Place tests in `src/core/tests.py`
- Run with: `python src/manage.py test core`

## Common Tasks for AI Assistants

### Adding a New Feature

1. Create/update models in `src/core/models.py`
2. Generate migrations: `python src/manage.py makemigrations`
3. Add views in `src/core/views.py`
4. Add URL patterns in `src/bamboolab/urls.py`
5. Create templates in `src/templates/`
6. Add static files in `src/static/`

### Modifying AI Processing

- Edit `src/core/tasks.py` for processing logic
- Adjust prompts in `generate_questions_from_files()`
- Update Document model fields if needed

### Adding New Subject

Subjects can be created via:
- Django admin (`/admin/`)
- Programmatically: `Subject.objects.create(name="Subject Name")`

### Debugging Celery Tasks

1. Check Celery worker logs
2. Verify Redis connection
3. Check Document status and error_message fields
4. Review logs in `process_document` task

## Port Configuration

| Service | Internal Port | External Port |
|---------|--------------|---------------|
| Django | 8000 | 8010 |
| PostgreSQL | 5452 | 5452 |
| Redis | 6379 | 7812 |

## Notes for Development

- The project uses Vietnamese language for UI/UX
- Celery broker URL in settings contains production Redis credentials - use env vars in docker-compose
- SQLite is default for local development; PostgreSQL for Docker/production
- Media files stored in `src/media/` (created at runtime)
- Remember to handle both `subject` (ForeignKey) and `subject_text` (legacy CharField) in questions
