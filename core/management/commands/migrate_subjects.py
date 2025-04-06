from django.core.management.base import BaseCommand
from core.models import Question, Document, Subject
from core.views import get_or_create_subject

class Command(BaseCommand):
    help = 'Chuyển dữ liệu từ trường subject_text (hoặc subject) sang model Subject mới'

    def handle(self, *args, **kwargs):
        self.stdout.write('Bắt đầu chuyển dữ liệu môn học...')
        
        # Lấy tất cả các tên môn học trong model Question
        if hasattr(Question, 'subject_text'):
            subject_names = set(Question.objects.exclude(subject_text__isnull=True)
                              .exclude(subject_text__exact='')
                              .values_list('subject_text', flat=True)
                              .distinct())
        else:
            # Nếu migration chưa chạy, vẫn còn trường subject
            subject_names = set(Question.objects.values_list('subject', flat=True).distinct())
        
        # Lấy tất cả các tên môn học trong model Document
        if hasattr(Document, 'subject_text'):
            document_subject_names = set(Document.objects.exclude(subject_text__isnull=True)
                                 .exclude(subject_text__exact='')
                                 .values_list('subject_text', flat=True)
                                 .distinct())
        else:
            # Nếu migration chưa chạy, vẫn còn trường subject
            document_subject_names = set(Document.objects.values_list('subject', flat=True).distinct())
        
        # Kết hợp tất cả các tên môn học
        all_subject_names = subject_names.union(document_subject_names)
        
        # Tạo các đối tượng Subject
        subjects_created = 0
        for name in all_subject_names:
            if not name:
                continue
                
            subject, created = Subject.objects.get_or_create(name=name)
            if created:
                subjects_created += 1
                self.stdout.write(f'  Đã tạo môn học mới: {name}')
        
        self.stdout.write(f'Đã tạo {subjects_created} môn học mới.')
        
        # Cập nhật các Question
        questions_updated = 0
        if hasattr(Question, 'subject_text'):
            for question in Question.objects.filter(subject=None).exclude(subject_text__isnull=True):
                if not question.subject_text:
                    continue
                    
                subject = get_or_create_subject(question.subject_text)
                question.subject = subject
                question.save(update_fields=['subject'])
                questions_updated += 1
        else:
            # Nếu migration chưa chạy, vẫn còn trường subject cũ
            for question in Question.objects.all():
                old_subject = getattr(question, 'subject', None)
                if not old_subject:
                    continue
                    
                subject = get_or_create_subject(old_subject)
                # Cần lưu tạm thời vào một trường khác để tránh xung đột
                question._new_subject = subject
            
            # Sau khi migration, cập nhật lại với subject mới
            if questions_updated > 0:
                self.stdout.write('Cần chạy migration trước và sau đó chạy lại lệnh này.')
        
        self.stdout.write(f'Đã cập nhật {questions_updated} câu hỏi.')
        
        # Cập nhật các Document
        documents_updated = 0
        if hasattr(Document, 'subject_text'):
            for document in Document.objects.filter(subject=None).exclude(subject_text__isnull=True):
                if not document.subject_text:
                    continue
                    
                subject = get_or_create_subject(document.subject_text)
                document.subject = subject
                document.save(update_fields=['subject'])
                documents_updated += 1
        else:
            # Tương tự như với Question
            for document in Document.objects.all():
                old_subject = getattr(document, 'subject', None)
                if not old_subject:
                    continue
                    
                subject = get_or_create_subject(old_subject)
                document._new_subject = subject
            
            if documents_updated > 0:
                self.stdout.write('Cần chạy migration trước và sau đó chạy lại lệnh này.')
        
        self.stdout.write(f'Đã cập nhật {documents_updated} tài liệu.')
        
        self.stdout.write(self.style.SUCCESS('Hoàn thành chuyển dữ liệu môn học!')) 