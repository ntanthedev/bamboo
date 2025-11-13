from django.shortcuts import render, redirect, get_object_or_404
import csv
import os
from django.conf import settings
from .models import Candidate, Question, Answer, Document, UploadedFile, Subject, InviteCode, QuizAttempt, UserAnswer
from django.db.models import Avg, Count
from django.contrib import messages
import random
from django.http import JsonResponse, HttpResponseNotFound
from .tasks import process_document
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
import dateutil.parser
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomUserCreationForm, QuizForm
from django.contrib.auth.models import User
from django.db import transaction

def get_or_create_subject(subject_name):
    """Lấy hoặc tạo Subject từ tên môn học"""
    if not subject_name:
        return None
    
    subject, created = Subject.objects.get_or_create(name=subject_name)
    return subject

def migrate_legacy_subject_data():
    """Hàm để chuyển dữ liệu từ trường subject cũ sang model Subject mới"""
    
    for doc in Document.objects.filter(subject=None):
        if not doc.subject_text:
            continue
        subject = get_or_create_subject(doc.subject_text)
        doc.subject = subject
        doc.save()
    
    for question in Question.objects.filter(subject=None):
        if not question.subject_text:
            continue
        subject = get_or_create_subject(question.subject_text)
        question.subject = subject
        question.save()

def home_view(request):
    """Hiển thị trang chủ của ứng dụng"""
    quiz_subjects = Subject.objects.all()
    
    question_count = Question.objects.count()
    document_count = Document.objects.count()
    
    context = {
        'quiz_subjects': quiz_subjects,
        'question_count': question_count,
        'document_count': document_count
    }
    
    return render(request, 'home.html', context)

def import_from_csv(request):
    Candidate.objects.all().delete()
    
    files_to_import = ['data1.csv', 'data2.csv']
    total_count = 0
    
    for csv_file in files_to_import:
        csv_file_path = os.path.join(settings.BASE_DIR, 'data', csv_file)
        
        if not os.path.exists(csv_file_path):
            messages.warning(request, f'Không tìm thấy dữ liệu điểm thi: {csv_file}')
            continue
        
        exam_type = csv_file.replace('.csv', '')
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)
                count = 0
                for line in reader:
                    if len(line) >= 11:
                        score_str = line[8].strip()
                        score_str = score_str.replace(',', '.')
                        
                        try:
                            score_float = float(score_str)
                        except ValueError:
                            messages.warning(request, f'Bỏ qua dòng với điểm không hợp lệ: {line[1]} - {score_str}')
                            continue
                        
                        clean_sbd = line[0].strip()
                            
                        Candidate.objects.create(
                            sbd = clean_sbd,
                            name = line[1],
                            birth = line[2],
                            place = line[3],
                            sex = line[4],
                            class_name = line[5],
                            school = line[6],
                            subject = line[7],
                            score = score_float,
                            rank = line[9],
                            prize = line[10],
                            exam_type = exam_type,
                        )
                        count += 1
                total_count += count
                messages.success(request, f'Đã nhập {count} thí sinh từ dữ liệu {csv_file} vào database')
        except Exception as e:
            messages.error(request, f'Lỗi đọc dữ liệu từ {csv_file}: {str(e)}')
    
    messages.success(request, f'Tổng cộng đã nhập {total_count} thí sinh vào database')
    return redirect('score-ranking')

def ScoreRanking(request):
    if request.method == 'GET':
        return render(request, 'tra-diem.html')
    elif request.method == 'POST':
        sbd = request.POST.get('sbd', '').strip()
        exam_type = request.POST.get('exam_type', 'data1')
        
        if Candidate.objects.count() == 0:
            csv_file_path = os.path.join(settings.BASE_DIR, 'data', f'{exam_type}.csv')
            
            if not os.path.exists(csv_file_path):
                return render(request, 'tra-diem.html', {'error': f'Không tìm thấy dữ liệu điểm thi cho kỳ thi {exam_type}'})
            
            try:
                with open(csv_file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    next(reader, None)
                    
                    for line in reader:
                        if len(line) >= 11:
                            score_str = line[8].strip()
                            score_str = score_str.replace(',', '.')
                            
                            try:
                                score_float = float(score_str)
                            except ValueError:
                                continue
                                
                            clean_sbd = line[0].strip()
                            
                            Candidate.objects.create(
                                sbd = clean_sbd,
                                name = line[1],
                                birth = line[2],
                                place = line[3],
                                sex = line[4],
                                class_name = line[5],
                                school = line[6],
                                subject = line[7],
                                score = score_float,
                                rank = line[9],
                                prize = line[10],
                                exam_type = exam_type,
                            )
            except Exception as e:
                return render(request, 'tra-diem.html', {'error': f'Lỗi đọc dữ liệu: {str(e)}'})
            
        try:
            candidate = Candidate.objects.filter(sbd=sbd, exam_type=exam_type).first()
            
            if not candidate:
                candidates = Candidate.objects.filter(sbd__icontains=sbd, exam_type=exam_type)
                if candidates.exists():
                    candidate = candidates.first()
            
            if not candidate:
                return render(request, 'tra-diem.html', {'error': f'Không tìm thấy thí sinh với số báo danh {sbd} trong kỳ thi được chọn'})
                
            top_score_subject = Candidate.objects.filter(
                subject=candidate.subject,
                exam_type=exam_type
            ).order_by('-score').first().score
            
            rank_desc = 100 - int(candidate.rank) if candidate.rank and candidate.rank.isdigit() else 95
            
            all_candidates = Candidate.objects.filter(exam_type=exam_type).count()
            better_score_all = Candidate.objects.filter(
                score__gt=candidate.score,
                exam_type=exam_type
            ).count()
            rank_position = better_score_all + 1
            
            average_score_subject = Candidate.objects.filter(
                subject=candidate.subject,
                exam_type=exam_type
            ).aggregate(Avg('score'))['score__avg']
            
            candidates_same_subject = Candidate.objects.filter(
                subject=candidate.subject,
                exam_type=exam_type
            ).count()
            candidates_better_or_equal = Candidate.objects.filter(
                subject=candidate.subject,
                score__gte=candidate.score,
                exam_type=exam_type
            ).count()
            subject_rank_position = candidates_better_or_equal
            
            subject_rank = max(1, min(100, round((subject_rank_position / candidates_same_subject) * 100)))
            if subject_rank_position == 1:
                subject_rank = 1
            
            subject_rank_desc = 100 - subject_rank
            
            current_score = float(candidate.score)
            higher_prize_info = None
            
            prize_rank = ['Nhất', 'Nhì', 'Ba', 'Khuyến khích', '']
            current_prize_index = -1
            
            for i, prize_name in enumerate(prize_rank):
                if candidate.prize and prize_name.lower() in candidate.prize.lower():
                    current_prize_index = i
                    break
            
            if current_prize_index == -1:
                current_prize_index = len(prize_rank) - 1
            
            if current_prize_index > 0:
                next_prize = prize_rank[current_prize_index - 1]
                higher_prize_candidates = Candidate.objects.filter(
                    subject=candidate.subject,
                    prize__icontains=next_prize,
                    exam_type=exam_type
                ).order_by('score')
                
                if higher_prize_candidates.exists():
                    min_score_for_higher_prize = higher_prize_candidates.first().score
                    points_needed = float(min_score_for_higher_prize) - current_score
                    
                    points_needed = round(points_needed, 2)
                    
                    higher_prize_info = {
                        'next_prize': next_prize,
                        'min_score': min_score_for_higher_prize,
                        'points_needed': points_needed
                    }
            
            exam_display_name = "Kỳ thi chọn HSG tỉnh lớp 11 tỉnh Hà Tĩnh"
            if exam_type == "data2":
                exam_display_name = "Kỳ thi chọn HSG tỉnh lớp 10 tễnh Hà Tĩnh"
            
            data_output = {
                'sbd': candidate.sbd,
                'name': candidate.name,
                'birth': candidate.birth,
                'place': candidate.place,
                'sex': candidate.sex,
                'class_name': candidate.class_name,
                'school': candidate.school,
                'subject': candidate.subject,
                'score': candidate.score,
                'rank': candidate.rank,
                'prize': candidate.prize,
                'top_score_subject': top_score_subject,
                'rank_desc': rank_desc,
                'rank_position': rank_position,
                'subject_rank': subject_rank,
                'subject_rank_desc': subject_rank_desc,
                'subject_rank_position': subject_rank_position,
                'count_all_candidate': all_candidates,
                'average_score_subject': round(average_score_subject, 2),
                'higher_prize_info': higher_prize_info,
                'exam_type': exam_type,
                'exam_display_name': exam_display_name,
            }
            return render(request, 'tra-diem.html', data_output)
            
        except Exception as e:
            return render(request, 'tra-diem.html', {'error': f'Lỗi xử lý dữ liệu: {str(e)}'})

def redirect_to_score_ranking(request):
    return redirect('score-ranking')

def quiz_list(request):
    """Hiển thị danh sách các câu hỏi trắc nghiệm theo môn học kèm số lượng câu hỏi"""
    subjects_with_counts = Subject.objects.annotate(question_count=Count('questions')).order_by('name')

    context = {
        'subjects_data': subjects_with_counts
    }
    return render(request, 'quiz-list.html', context)

@login_required
def start_quiz(request, subject_id):
    """Bắt đầu một lần làm bài mới."""
    subject = get_object_or_404(Subject, pk=subject_id)
    
    all_questions = list(Question.objects.filter(subject=subject))
    if len(all_questions) < 16:
        messages.warning(request, f"Môn {subject.name} chưa đủ 16 câu hỏi.")
        return redirect('quiz-list')
        
    selected_questions = random.sample(all_questions, 16)
    
    attempt = QuizAttempt.objects.create(user=request.user, subject=subject)
    attempt.questions.set(selected_questions)
    
    return redirect('take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    """Hiển thị trang làm bài với tất cả câu hỏi."""
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user, completed=False)
    questions = attempt.questions.prefetch_related('answer_set').all()
    
    form = QuizForm(questions=questions)
    
    time_limit_seconds = 30 * 60 
    elapsed_seconds = (timezone.now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, time_limit_seconds - elapsed_seconds)
    
    context = {
        'attempt': attempt,
        'subject': attempt.subject,
        'questions': questions,
        'form': form,
        'remaining_seconds': int(remaining_seconds),
    }
    return render(request, 'take-quiz.html', context)

@login_required
@transaction.atomic
def submit_quiz(request, attempt_id):
    """Xử lý việc nộp bài."""
    if request.method != 'POST':
        return redirect('take_quiz', attempt_id=attempt_id)

    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user, completed=False)
    questions = attempt.questions.prefetch_related('answer_set').all()
    form = QuizForm(request.POST, questions=questions)

    if form.is_valid():
        attempt.completed = True
        attempt.end_time = timezone.now()
        attempt.save()

        UserAnswer.objects.filter(quiz_attempt=attempt).delete()
        for question in questions:
            field_name = f'question_{question.id}'
            selected_answer_id = form.cleaned_data.get(field_name)
            if selected_answer_id:
                try:
                    selected_answer = Answer.objects.get(pk=selected_answer_id, question=question)
                    UserAnswer.objects.create(
                        quiz_attempt=attempt,
                        question=question,
                        selected_answer=selected_answer
                    )
                except Answer.DoesNotExist:
                    messages.warning(request, f"Có lỗi khi lưu đáp án cho câu hỏi ID {question.id}.")
                    pass 
        
        score = attempt.calculate_score()

        messages.success(request, f"Bạn đã hoàn thành bài kiểm tra môn {attempt.subject.name}! Điểm của bạn là {score:.2f}/10.")
        return redirect('quiz_result', attempt_id=attempt.id) 
    else:
        messages.error(request, "Vui lòng trả lời tất cả các câu hỏi.")
        time_limit_seconds = 30 * 60 
        elapsed_seconds = (timezone.now() - attempt.start_time).total_seconds()
        remaining_seconds = max(0, time_limit_seconds - elapsed_seconds)
        context = {
            'attempt': attempt,
            'subject': attempt.subject,
            'questions': questions,
            'form': form,
            'remaining_seconds': int(remaining_seconds),
        }
        return render(request, 'take-quiz.html', context)

@login_required
def quiz_result(request, attempt_id):
    """Hiển thị kết quả bài kiểm tra."""
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user, completed=True)
    user_answers_dict = {ua.question_id: ua.selected_answer_id for ua in attempt.user_answers.all()}
    questions = attempt.questions.prefetch_related('answer_set').all()

    correct_answers = Answer.objects.filter(question__in=questions, is_correct=True)
    correct_answer_ids_map = {answer.question_id: answer.id for answer in correct_answers}

    correct_answers_count = 0
    total_questions = questions.count()
    if total_questions > 0:
        for question_id, selected_answer_id in user_answers_dict.items():
            if selected_answer_id == correct_answer_ids_map.get(question_id):
                correct_answers_count += 1

    context = {
        'attempt': attempt,
        'subject': attempt.subject,
        'questions': questions,
        'user_answers': user_answers_dict,
        'score': attempt.score,
        'correct_answers_count': correct_answers_count,
        'total_questions': total_questions,
        'correct_answer_ids_map': correct_answer_ids_map
    }
    return render(request, 'quiz-result.html', context)

@user_passes_test(lambda u: u.is_staff)
def upload_document(request):
    """View để xử lý việc upload tài liệu và tạo câu hỏi tự động"""
    if request.method == 'POST':
        title = request.POST.get('title')
        subject_id = request.POST.get('subject')
        uploaded_files = request.FILES.getlist('document_file')
        additional_requirements = request.POST.get('additional_requirements', '')
        
        if not uploaded_files:
            messages.error(request, 'Vui lòng chọn ít nhất một tệp tài liệu để upload.')
            subjects = Subject.objects.all()
            return render(request, 'upload-document.html', {'subjects': subjects, 'title': title, 'subject_id': subject_id, 'additional_requirements': additional_requirements})

        if not all([title, subject_id]): 
            messages.error(request, 'Vui lòng điền đầy đủ Tiêu đề và Môn học.')
            subjects = Subject.objects.all()
            return render(request, 'upload-document.html', {'subjects': subjects, 'title': title, 'subject_id': subject_id, 'additional_requirements': additional_requirements})
        
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            messages.error(request, 'Môn học không hợp lệ.')
            subjects = Subject.objects.all()
            return render(request, 'upload-document.html', {'subjects': subjects, 'title': title, 'subject_id': subject_id, 'additional_requirements': additional_requirements})
        
        document = Document.objects.create(
            title=title,
            author=request.user,
            subject=subject,
            status='pending',
            additional_requirements=additional_requirements
        )
        
        files_saved = 0
        for uploaded_file in uploaded_files:
            try:
                UploadedFile.objects.create(
                    document=document,
                    file=uploaded_file
                )
                files_saved += 1
            except Exception as e:
                messages.warning(request, f"Lỗi khi lưu tệp {uploaded_file.name}: {e}")
        
        if files_saved == 0:
            document.delete()
            messages.error(request, "Đã xảy ra lỗi, không thể lưu tệp nào.")
            subjects = Subject.objects.all()
            return render(request, 'upload-document.html', {'subjects': subjects, 'title': title, 'subject_id': subject_id, 'additional_requirements': additional_requirements})

        task = process_document.delay(document.id, additional_requirements)
        
        document.task_id = task.id
        document.save()
        
        messages.success(request, f"Đã nhận {files_saved} tệp. Tài liệu đang được xử lý...")
        return redirect('document-status', document_id=document.id)
    
    subjects = Subject.objects.all()
    return render(request, 'upload-document.html', {'subjects': subjects})

@user_passes_test(lambda u: u.is_staff)
def document_status(request, document_id):  
    """View để hiển thị trạng thái xử lý tài liệu"""
    document = get_object_or_404(Document, id=document_id)
    
    questions = Question.objects.filter(document=document)
    question_count = questions.count()
    
    context = {
        'document': document,
        'question_count': question_count,
        'questions': questions
    }
    
    return render(request, 'document-status.html', context)

@user_passes_test(lambda u: u.is_staff)
def document_status_api(request, document_id):
    """API endpoint để lấy thông tin tiến trình xử lý tài liệu"""
    try:
        document = Document.objects.get(id=document_id)
        data = {
            'status': document.status,
            'progress': document.progress,
            'progress_message': document.progress_message or "",
            'error_message': document.error_message or "",
            'question_count': Question.objects.filter(document=document).count()
        }
        return JsonResponse(data)
    except Document.DoesNotExist:
        return HttpResponseNotFound("Document not found")

def LoginView(request):
    """Xử lý đăng nhập người dùng."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember') == 'on'
        
        if not username or not password:
            messages.error(request, 'Vui lòng nhập cả tên tài khoản và mật khẩu.')
            return render(request, 'login.html')
        
        try:
            user_check = User.objects.get(username=username)
            user = authenticate(request, username=user_check.username, password=password)
        except User.DoesNotExist:
            user = None
            

        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
                
            messages.success(request, f'Chào mừng {user.first_name or user.username} quay trở lại!')
            
            next_url = request.POST.get('next', reverse('home'))
            return redirect(next_url)
        else:
            messages.error(request, 'Tên tài khoản hoặc mật khẩu không đúng.')
            return render(request, 'login.html', {'username': username})
    else:
        return render(request, 'login.html')

def LogoutView(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect('home')

def RegisterView(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            
            username = user.username
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Tài khoản {username} đã được tạo thành công!")
                return redirect('home')
            else:
                pass
            
    else:
        initial_data = {}
        invite_code = request.GET.get('ref')
        if invite_code:
            initial_data['invite_code'] = invite_code
        form = CustomUserCreationForm(initial=initial_data)
        
    return render(request, 'register.html', {'form': form})

def document_list(request):
    """Hiển thị danh sách các tài liệu đã tải lên."""
    documents = Document.objects.annotate(
        question_count=Count('questions'),
        files_count=Count('uploaded_files')
    ).select_related('subject').order_by('-uploaded_at')
    
    context = {
        'documents': documents
    }
    return render(request, 'document-list.html', context)

def document_questions(request, document_id):
    """Hiển thị danh sách câu hỏi của một tài liệu cụ thể."""
    document = get_object_or_404(Document, pk=document_id)
    questions = document.questions.all()
    context = {
        'document': document,
        'questions': questions
    }
    return render(request, 'document-questions.html', context)

@login_required
def user_profile(request):
    """Hiển thị trang cá nhân của người dùng với lịch sử làm bài."""
    user = request.user
    quiz_attempts = QuizAttempt.objects.filter(user=user, completed=True)\
                                     .select_related('subject')\
                                     .order_by('-end_time')

    context = {
        'user': user,
        'quiz_attempts': quiz_attempts,
    }
    return render(request, 'profile.html', context)
