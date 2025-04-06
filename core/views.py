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
    # Chuyển dữ liệu từ Document
    for doc in Document.objects.filter(subject=None):
        if not doc.subject_text:
            continue
        subject = get_or_create_subject(doc.subject_text)
        doc.subject = subject
        doc.save()
    
    # Chuyển dữ liệu từ Question
    for question in Question.objects.filter(subject=None):
        if not question.subject_text:
            continue
        subject = get_or_create_subject(question.subject_text)
        question.subject = subject
        question.save()

# Create your views here.

def home_view(request):
    """Hiển thị trang chủ của ứng dụng"""
    # Lấy danh sách các môn học trắc nghiệm
    quiz_subjects = Subject.objects.all()
    
    # Lấy số lượng câu hỏi và tài liệu
    question_count = Question.objects.count()
    document_count = Document.objects.count()
    
    context = {
        'quiz_subjects': quiz_subjects,
        'question_count': question_count,
        'document_count': document_count
    }
    
    return render(request, 'home.html', context)

def import_from_csv(request):
    # Xóa dữ liệu cũ (nếu cần) trước khi tải dữ liệu mới
    Candidate.objects.all().delete()
    
    # Nhập dữ liệu từ cả hai file
    files_to_import = ['data1.csv', 'data2.csv']
    total_count = 0
    
    for csv_file in files_to_import:
        # Đường dẫn đầy đủ đến file CSV
        csv_file_path = os.path.join(settings.BASE_DIR, 'data', csv_file)
        
        # Kiểm tra sự tồn tại của file CSV
        if not os.path.exists(csv_file_path):
            messages.warning(request, f'Không tìm thấy dữ liệu điểm thi: {csv_file}')
            continue
        
        # Xác định loại kỳ thi dựa vào tên file
        exam_type = csv_file.replace('.csv', '')
        
        # Đọc dữ liệu từ file CSV
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)  # Bỏ qua header nếu có
                count = 0
                for line in reader:
                    if len(line) >= 11:  # Đảm bảo đủ cột dữ liệu
                        # Xử lý điểm số (thay thế dấu phẩy bằng dấu chấm và loại bỏ khoảng trắng)
                        score_str = line[8].strip()
                        score_str = score_str.replace(',', '.')
                        
                        try:
                            score_float = float(score_str)
                        except ValueError:
                            messages.warning(request, f'Bỏ qua dòng với điểm không hợp lệ: {line[1]} - {score_str}')
                            continue
                        
                        # Chuẩn hóa số báo danh bằng cách loại bỏ khoảng trắng
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
                            exam_type = exam_type,  # Thêm trường để phân biệt loại kỳ thi
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
        sbd = request.POST.get('sbd', '').strip()  # Loại bỏ khoảng trắng ở đầu và cuối
        exam_type = request.POST.get('exam_type', 'data1')  # Mặc định là kỳ thi lớp 11 nếu không chọn
        
        # Kiểm tra xem database có dữ liệu chưa, nếu chưa thì tải từ CSV
        if Candidate.objects.count() == 0:
            # Đường dẫn đầy đủ đến file CSV
            csv_file_path = os.path.join(settings.BASE_DIR, 'data', f'{exam_type}.csv')
            
            # Kiểm tra sự tồn tại của file CSV
            if not os.path.exists(csv_file_path):
                return render(request, 'tra-diem.html', {'error': f'Không tìm thấy dữ liệu điểm thi cho kỳ thi {exam_type}'})
            
            # Đọc dữ liệu từ file CSV
            try:
                with open(csv_file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    next(reader, None)  # Bỏ qua header nếu có
                    
                    for line in reader:
                        if len(line) >= 11:  # Đảm bảo đủ cột dữ liệu
                            # Xử lý điểm số (thay thế dấu phẩy bằng dấu chấm và loại bỏ khoảng trắng)
                            score_str = line[8].strip()
                            score_str = score_str.replace(',', '.')
                            
                            try:
                                score_float = float(score_str)
                            except ValueError:
                                continue  # Bỏ qua dòng với điểm không hợp lệ
                                
                            # Chuẩn hóa số báo danh bằng cách loại bỏ khoảng trắng
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
            
        # Tìm thí sinh theo số báo danh và loại kỳ thi
        try:
            # Tìm kiếm chính xác trước
            candidate = Candidate.objects.filter(sbd=sbd, exam_type=exam_type).first()
            
            # Nếu không tìm thấy, thử tìm kiếm có chứa số báo danh
            if not candidate:
                candidates = Candidate.objects.filter(sbd__icontains=sbd, exam_type=exam_type)
                if candidates.exists():
                    candidate = candidates.first()
            
            if not candidate:
                return render(request, 'tra-diem.html', {'error': f'Không tìm thấy thí sinh với số báo danh {sbd} trong kỳ thi được chọn'})
                
            # Tìm điểm cao nhất của môn học trong cùng kỳ thi
            top_score_subject = Candidate.objects.filter(
                subject=candidate.subject,
                exam_type=exam_type
            ).order_by('-score').first().score
            
            # Tính phần trăm còn lại từ rank (nếu rank = 5%, thì rank_desc = 95%)
            rank_desc = 100 - int(candidate.rank) if candidate.rank and candidate.rank.isdigit() else 95
            
            # Tính vị trí thứ hạng toàn khóa trong cùng kỳ thi
            all_candidates = Candidate.objects.filter(exam_type=exam_type).count()
            better_score_all = Candidate.objects.filter(
                score__gt=candidate.score,
                exam_type=exam_type
            ).count()
            rank_position = better_score_all + 1  # +1 vì thứ hạng bắt đầu từ 1
            
            #điểm trung bình môn học trong cùng kỳ thi
            average_score_subject = Candidate.objects.filter(
                subject=candidate.subject,
                exam_type=exam_type
            ).aggregate(Avg('score'))['score__avg']
            
            # Tính xếp hạng trong môn học trong cùng kỳ thi
            candidates_same_subject = Candidate.objects.filter(
                subject=candidate.subject,
                exam_type=exam_type
            ).count()
            # Đếm số thí sinh có điểm cao hơn hoặc bằng
            candidates_better_or_equal = Candidate.objects.filter(
                subject=candidate.subject,
                score__gte=candidate.score,
                exam_type=exam_type
            ).count()
            # Lấy thứ hạng (1 là cao nhất)
            subject_rank_position = candidates_better_or_equal
            
            # Tính phần trăm top trong môn học (1% là cao nhất)
            subject_rank = max(1, min(100, round((subject_rank_position / candidates_same_subject) * 100)))
            if subject_rank_position == 1:  # Nếu là thứ hạng 1 thì luôn là top 1%
                subject_rank = 1
            
            subject_rank_desc = 100 - subject_rank  # Phần trăm còn lại cao hơn
            
            # Xác định giải cao hơn và điểm cần đạt
            current_score = float(candidate.score)
            higher_prize_info = None
            
            # Danh sách các giải từ cao đến thấp
            prize_rank = ['Nhất', 'Nhì', 'Ba', 'Khuyến khích', '']
            current_prize_index = -1
            
            # Tìm vị trí giải hiện tại trong danh sách
            for i, prize_name in enumerate(prize_rank):
                if candidate.prize and prize_name.lower() in candidate.prize.lower():
                    current_prize_index = i
                    break
            
            # Nếu không xác định được giải, mặc định là không có giải
            if current_prize_index == -1:
                current_prize_index = len(prize_rank) - 1
            
            # Nếu đã có giải cao nhất thì không cần thông báo
            if current_prize_index > 0:  # Có giải và không phải giải Nhất
                # Tìm thí sinh có giải cao hơn 1 bậc trong cùng môn và cùng kỳ thi
                next_prize = prize_rank[current_prize_index - 1]
                higher_prize_candidates = Candidate.objects.filter(
                    subject=candidate.subject,
                    prize__icontains=next_prize,
                    exam_type=exam_type
                ).order_by('score')
                
                if higher_prize_candidates.exists():
                    min_score_for_higher_prize = higher_prize_candidates.first().score
                    points_needed = float(min_score_for_higher_prize) - current_score
                    
                    # Làm tròn đến 2 chữ số thập phân
                    points_needed = round(points_needed, 2)
                    
                    higher_prize_info = {
                        'next_prize': next_prize,
                        'min_score': min_score_for_higher_prize,
                        'points_needed': points_needed
                    }
            
            # Lấy tên kỳ thi hiển thị
            exam_display_name = "Kỳ thi chọn HSG tỉnh lớp 11 tỉnh Hà Tĩnh"
            if exam_type == "data2":
                exam_display_name = "Kỳ thi chọn HSG tỉnh lớp 10 tỉnh Hà Tĩnh"
            
            # Truyền dữ liệu vào template
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
    # Lấy danh sách môn học và đếm số câu hỏi cho mỗi môn
    subjects_with_counts = Subject.objects.annotate(question_count=Count('questions')).order_by('name')

    context = {
        'subjects_data': subjects_with_counts
    }
    return render(request, 'quiz-list.html', context)

@login_required
def start_quiz(request, subject_id):
    """Bắt đầu một lần làm bài mới."""
    subject = get_object_or_404(Subject, pk=subject_id)
    
    # Lấy câu hỏi ngẫu nhiên (ví dụ 16 câu)
    all_questions = list(Question.objects.filter(subject=subject))
    if len(all_questions) < 16:
        messages.warning(request, f"Môn {subject.name} chưa đủ 16 câu hỏi.")
        return redirect('quiz-list')
        
    selected_questions = random.sample(all_questions, 16)
    
    # Tạo bản ghi QuizAttempt
    attempt = QuizAttempt.objects.create(user=request.user, subject=subject)
    attempt.questions.set(selected_questions)
    
    # Chuyển hướng đến trang làm bài
    return redirect('take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    """Hiển thị trang làm bài với tất cả câu hỏi."""
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user, completed=False)
    questions = attempt.questions.prefetch_related('answer_set').all()
    
    # Tạo form động dựa trên câu hỏi
    form = QuizForm(questions=questions)
    
    # Tính thời gian còn lại (ví dụ: 30 phút)
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
@transaction.atomic # Đảm bảo các thao tác DB là một khối
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
        attempt.save() # Lưu trạng thái hoàn thành và thời gian kết thúc

        # Lưu các câu trả lời của người dùng
        UserAnswer.objects.filter(quiz_attempt=attempt).delete() # Xóa câu trả lời cũ nếu có (đề phòng submit lại)
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
                    # Bỏ qua nếu ID đáp án không hợp lệ (dữ liệu POST bị sửa đổi)
                    messages.warning(request, f"Có lỗi khi lưu đáp án cho câu hỏi ID {question.id}.")
                    pass 
        
        # Tính điểm
        score = attempt.calculate_score()

        # Chuyển hướng đến trang kết quả (cần tạo view và template này)
        messages.success(request, f"Bạn đã hoàn thành bài kiểm tra môn {attempt.subject.name}! Điểm của bạn là {score:.2f}/10.")
        return redirect('quiz_result', attempt_id=attempt.id) 
    else:
        # Form không hợp lệ (ví dụ: bỏ sót câu hỏi nếu bắt buộc)
        messages.error(request, "Vui lòng trả lời tất cả các câu hỏi.")
        # Hiển thị lại trang làm bài với lỗi
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

    # Lấy ID của các đáp án đúng cho các câu hỏi trong lần thi này
    correct_answers = Answer.objects.filter(question__in=questions, is_correct=True)
    correct_answer_ids_map = {answer.question_id: answer.id for answer in correct_answers}

    # Tính toán số câu trả lời đúng trong view
    correct_answers_count = 0
    total_questions = questions.count()
    if total_questions > 0:
        for question_id, selected_answer_id in user_answers_dict.items():
            # Sử dụng map đã tạo để kiểm tra
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
        'correct_answer_ids_map': correct_answer_ids_map # Truyền map vào context
    }
    return render(request, 'quiz-result.html', context)

@user_passes_test(lambda u: u.is_staff)
def upload_document(request):
    """View để xử lý việc upload tài liệu và tạo câu hỏi tự động"""
    if request.method == 'POST':
        title = request.POST.get('title')
        subject_id = request.POST.get('subject')
        # Lấy danh sách các file upload
        uploaded_files = request.FILES.getlist('document_file') 
        # Lấy yêu cầu bổ sung
        additional_requirements = request.POST.get('additional_requirements', '') 
        
        # --- VALIDATION --- 
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
        # --- END VALIDATION ---
        
        # 1. Tạo đối tượng Document chính
        document = Document.objects.create(
            title=title,
            author=request.user,
            subject=subject,
            status='pending',
            additional_requirements=additional_requirements
        )
        
        # 2. Lặp qua các file và tạo đối tượng UploadedFile tương ứng
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
        
        # Kiểm tra xem có lưu được file nào không
        if files_saved == 0:
            document.delete()
            messages.error(request, "Đã xảy ra lỗi, không thể lưu tệp nào.")
            subjects = Subject.objects.all()
            return render(request, 'upload-document.html', {'subjects': subjects, 'title': title, 'subject_id': subject_id, 'additional_requirements': additional_requirements})

        # 3. Gửi task để xử lý tài liệu trong background
        task = process_document.delay(document.id, additional_requirements)
        
        # 4. Lưu task_id để theo dõi tiến trình
        document.task_id = task.id
        document.save()
        
        messages.success(request, f"Đã nhận {files_saved} tệp. Tài liệu đang được xử lý...")
        # 5. Chuyển hướng đến trang theo dõi trạng thái
        return redirect('document-status', document_id=document.id)
    
    # GET request
    subjects = Subject.objects.all()
    return render(request, 'upload-document.html', {'subjects': subjects})

@user_passes_test(lambda u: u.is_staff)
def document_status(request, document_id):  
    """View để hiển thị trạng thái xử lý tài liệu"""
    document = get_object_or_404(Document, id=document_id)
    
    # Lấy danh sách câu hỏi đã tạo (nếu có)
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
        return redirect('home') # Redirect if already logged in

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember') == 'on' # Check if checkbox is checked
        
        if not username or not password:
            messages.error(request, 'Vui lòng nhập cả tên tài khoản và mật khẩu.')
            return render(request, 'login.html')
        
        # Authenticate using email (assuming email is the username or you have a custom backend)
        # We need to fetch the username associated with the email first
        try:
            user_check = User.objects.get(username=username)
            user = authenticate(request, username=user_check.username, password=password)
        except User.DoesNotExist:
            user = None
            

        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30) # 30 days expiry
            else:
                request.session.set_expiry(0) # Session ends when browser closes
                
            messages.success(request, f'Chào mừng {user.first_name or user.username} quay trở lại!')
            
            # Redirect to the next page or home
            next_url = request.POST.get('next', reverse('home'))
            return redirect(next_url)
        else:
            messages.error(request, 'Tên tài khoản hoặc mật khẩu không đúng.')
            # Pass the email back to the template to pre-fill the field
            return render(request, 'login.html', {'username': username})
    else:
        # GET request, just show the login form
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
            
            # Lưu session nếu chọn remember_me
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 ngày
            else:
                request.session.set_expiry(0)  # Đóng browser là hết session
            
            # Đăng nhập người dùng sau khi đăng ký
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
        # Kiểm tra xem có mã giới thiệu từ URL không
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
        files_count=Count('uploaded_files') # Đếm số lượng file tải lên cho mỗi document
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
    # Lấy các lần làm bài đã hoàn thành, sắp xếp theo thời gian kết thúc mới nhất
    # Sử dụng select_related để tối ưu truy vấn thông tin môn học
    quiz_attempts = QuizAttempt.objects.filter(user=user, completed=True)\
                                     .select_related('subject')\
                                     .order_by('-end_time')

    context = {
        'user': user,
        'quiz_attempts': quiz_attempts,
    }
    return render(request, 'profile.html', context)
