"""
URL configuration for bamboolab project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    ScoreRanking, 
    redirect_to_score_ranking, 
    import_from_csv,
    quiz_list,
    start_quiz,
    take_quiz,
    submit_quiz,
    quiz_result,
    upload_document,
    document_status,
    home_view,
    document_status_api,
    LoginView,
    LogoutView,
    RegisterView,
    document_list,
    document_questions,
    user_profile
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("score-ranking/", ScoreRanking, name="score-ranking"),
    path("import-csv/", import_from_csv, name="import-csv"),
    
    # URL cho chức năng trắc nghiệm
    path("quiz/", quiz_list, name="quiz-list"),
    path("quiz/start/<int:subject_id>/", start_quiz, name="start_quiz"),
    path("quiz/attempt/<uuid:attempt_id>/", take_quiz, name="take_quiz"),
    path("quiz/submit/<uuid:attempt_id>/", submit_quiz, name="submit_quiz"),
    path("quiz/result/<uuid:attempt_id>/", quiz_result, name="quiz_result"),
    
    # URL cho chức năng upload tài liệu và tạo câu hỏi tự động
    path("upload-document/", upload_document, name="upload-document"),
    path("document-status/<int:document_id>/", document_status, name="document-status"),
    path("api/document-status/<int:document_id>/", document_status_api, name="document-status-api"),
    
    # URLs cho danh sách tài liệu
    path("documents/", document_list, name="document-list"),
    path("documents/<int:document_id>/questions/", document_questions, name="document-questions"),

    
    # Hệ thống kiểm soát người dùng
    path("login/", LoginView, name="login_view"),
    path("logout/", LogoutView, name="logout_view"),
    path("register/", RegisterView, name="register_view"),
    # Trang cá nhân
    path("profile/", user_profile, name="user_profile"),
    # Trang chủ
    path("", home_view, name="home"),
    
]

# Thêm cấu hình để phục vụ các file media trong chế độ development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
