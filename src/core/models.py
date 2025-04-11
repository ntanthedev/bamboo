from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone

class Subject(models.Model):
    """
    Model lưu trữ thông tin về các môn học.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên môn học")
    code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Mã môn học")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Môn học"
        verbose_name_plural = "Môn học"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def question_count(self):
        """Trả về số lượng câu hỏi của môn học này"""
        return self.questions.count()

# Create your models here.
class Candidate(models.Model):
    sbd = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    birth = models.CharField(max_length=200)
    place = models.CharField(max_length=200)
    sex = models.CharField(max_length=200)
    class_name = models.CharField(max_length=200)
    school = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    score = models.FloatField()
    rank = models.CharField(max_length=200)
    prize = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=50, default='data1')  # Mặc định là kỳ thi lớp 11

    class Meta:
        verbose_name = "Thí sinh"
        verbose_name_plural = "Thí sinh"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.sbd} - {self.subject} - {self.exam_type}"

class Question(models.Model):
    text = models.TextField()
    subject_text = models.CharField(max_length=100, verbose_name="Tên môn học (cũ)", null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions', verbose_name="Môn học", null=True)
    difficulty = models.CharField(max_length=20, choices=[
        ('easy', 'Dễ'),
        ('medium', 'Trung bình'),
        ('hard', 'Khó')
    ], default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    document = models.ForeignKey('Document', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')

    class Meta:
        verbose_name = "Câu hỏi"
        verbose_name_plural = "Câu hỏi"
        ordering = ['created_at']

    def __str__(self):
        return self.text[:50]
    
    def get_answers(self):
        return self.answer_set.all()

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.TextField("Nội dung đáp án")
    is_correct = models.BooleanField("Là đáp án đúng", default=False)
    explanation = models.TextField("Giải thích đáp án", blank=True, null=True)
    position = models.IntegerField(default=0)  # Vị trí hiển thị của đáp án
    
    class Meta:
        verbose_name = "Đáp án"
        verbose_name_plural = "Đáp án"
        ordering = ['position']

    def __str__(self):
        return f"{'Correct' if self.is_correct else 'Incorrect'}: {self.text[:50]}..."

class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Đang chờ xử lý'),
        ('processing', 'Đang xử lý'),
        ('completed', 'Hoàn thành'),
        ('failed', 'Thất bại')
    ]
    
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='documents', verbose_name="Môn học", null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents', verbose_name="Tác giả", null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    task_id = models.CharField(max_length=255, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    additional_requirements = models.TextField(blank=True, null=True)
    progress = models.IntegerField(default=0, help_text="Tiến trình xử lý (0-100%)")
    progress_message = models.CharField(max_length=255, blank=True, null=True, help_text="Thông báo về tiến trình hiện tại")
    
    class Meta:
        verbose_name = "Tài liệu"
        verbose_name_plural = "Tài liệu"
        ordering = ['uploaded_at']

    def __str__(self):
        return self.title

# Model mới để lưu từng file upload
class UploadedFile(models.Model):
    document = models.ForeignKey(Document, related_name='uploaded_files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='document_files/') # Lưu file vào thư mục riêng
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tệp upload"
        verbose_name_plural = "Tệp upload"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"File for {self.document.title} - {self.file.name}"

# Model lưu thông tin profile của user
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    invite_code = models.ForeignKey('InviteCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_users')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Số điện thoại")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile của {self.user.username}"

# Model cho mã giới thiệu
class InviteCode(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã giới thiệu")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_referral_codes', verbose_name="Người tạo")
    created_at = models.DateTimeField(auto_now_add=True)
    remaining_uses = models.PositiveIntegerField(default=10, verbose_name="Số lần sử dụng")
    is_active = models.BooleanField(default=True, verbose_name="Còn hiệu lực")
    
    def __str__(self):
        return f"{self.code} - Còn {self.remaining_uses} lần sử dụng"
    
    def use_code(self):
        """Sử dụng mã giới thiệu và giảm số lần sử dụng đi 1"""
        if self.remaining_uses > 0 and self.is_active:
            self.remaining_uses -= 1
            # Nếu hết lượt, đánh dấu là không còn hiệu lực
            if self.remaining_uses == 0:
                self.is_active = False
            self.save()
            return True
        return False
    
    class Meta:
        verbose_name = "Mã giới thiệu"
        verbose_name_plural = "Mã giới thiệu"

class QuizAttempt(models.Model):
    """Lưu thông tin một lần làm bài kiểm tra của người dùng."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    questions = models.ManyToManyField(Question, related_name='attempts')
    score = models.FloatField(null=True, blank=True, help_text="Điểm số trên thang 10")
    completed = models.BooleanField(default=False)
    # Có thể thêm trường lưu tổng thời gian làm bài nếu muốn

    def __str__(self):
        return f"Bài kiểm tra {self.subject.name} của {self.user.username} ({self.start_time.strftime('%d/%m/%Y %H:%M')})"

    def calculate_score(self):
        """Tính điểm dựa trên các câu trả lời đã lưu trong UserAnswer."""
        if not self.completed:
            return None
            
        user_answers = self.user_answers.select_related('selected_answer').all()
        correct_count = 0
        total_questions = self.questions.count()
        
        if total_questions == 0:
            return 0.0

        correct_answer_ids = set(Answer.objects.filter(question__in=self.questions.all(), is_correct=True).values_list('id', flat=True))

        for ua in user_answers:
            if ua.selected_answer_id in correct_answer_ids:
                correct_count += 1
                
        # Tính điểm thang 10
        self.score = round((correct_count / total_questions) * 10, 2)
        self.save()
        return self.score

    class Meta:
        ordering = ['-start_time']
        verbose_name = "Lần làm bài"
        verbose_name_plural = "Các lần làm bài"

class UserAnswer(models.Model):
    """Lưu câu trả lời người dùng đã chọn cho một câu hỏi trong một lần làm bài."""
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Đáp án của {self.quiz_attempt.user.username} cho câu hỏi {self.question.id} trong lần làm bài {self.quiz_attempt.id}"

    class Meta:
        unique_together = ('quiz_attempt', 'question') # Đảm bảo mỗi câu hỏi chỉ có 1 đáp án được lưu cho mỗi lần làm bài
        verbose_name = "Câu trả lời của người dùng"
        verbose_name_plural = "Các câu trả lời của người dùng"
