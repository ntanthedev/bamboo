from django.contrib import admin
from .models import (
    Candidate, Question, Answer, Document, UploadedFile, Subject, 
    UserProfile, InviteCode, QuizAttempt, UserAnswer
)

# Register your models here.
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'sbd', 'subject', 'score', 'rank', 'prize', 'exam_type')
    search_fields = ('name', 'sbd')
    list_filter = ('subject', 'exam_type', 'prize')

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'text_short', 'subject', 'difficulty', 'created_at']
    list_filter = ['subject', 'difficulty', 'created_at']
    search_fields = ['text', 'subject__name']
    inlines = [AnswerInline]
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Câu hỏi'

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct', 'explanation')
    list_filter = ('is_correct', 'question__subject')
    search_fields = ('text', 'question__text')
    fields = ('question', 'text', 'is_correct', 'explanation')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'subject', 'status', 'uploaded_at', 'progress']
    list_filter = ['subject', 'status', 'uploaded_at']
    search_fields = ['title', 'subject__name']
    readonly_fields = ['task_id', 'uploaded_at', 'progress', 'progress_message']

class UploadedFileInline(admin.TabularInline):
    model = UploadedFile
    extra = 1
    readonly_fields = ['uploaded_at']

class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'question_count', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']

admin.site.register(Subject, SubjectAdmin)

class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'created_by', 'remaining_uses', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'created_by__username']
    readonly_fields = ['created_at']
    
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_email', 'invite_code', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_filter = ['created_at']
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

# Đăng ký các model mới
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(InviteCode, InviteCodeAdmin)

class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0 # Không hiển thị thêm dòng trống
    readonly_fields = ('question', 'selected_answer', 'submitted_at')
    can_delete = False # Không cho xóa câu trả lời qua admin

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'start_time', 'end_time', 'score', 'completed')
    list_filter = ('subject', 'completed', 'start_time')
    search_fields = ('user__username', 'subject__name')
    readonly_fields = ('id', 'user', 'subject', 'start_time', 'end_time', 'questions')
    inlines = [UserAnswerInline]
    
    def get_readonly_fields(self, request, obj=None):
        # Chỉ cho phép sửa điểm và trạng thái hoàn thành nếu cần
        if obj:
            return self.readonly_fields + ('score', 'completed') 
        return self.readonly_fields

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('quiz_attempt', 'question', 'selected_answer', 'submitted_at')
    list_filter = ('quiz_attempt__subject', 'submitted_at')
    search_fields = ('quiz_attempt__user__username', 'question__text', 'selected_answer__text')
    readonly_fields = ('quiz_attempt', 'question', 'selected_answer', 'submitted_at')
