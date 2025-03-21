from django.shortcuts import render, redirect
import csv
import os
from django.conf import settings
from .models import Candidate
from django.db.models import Avg
from django.contrib import messages
# Create your views here.

def import_from_csv(request):
    # Xóa dữ liệu cũ (nếu cần) trước khi tải dữ liệu mới
    Candidate.objects.all().delete()
    
    # Đường dẫn đầy đủ đến file CSV
    csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'data.csv')
    
    # Kiểm tra sự tồn tại của file CSV
    if not os.path.exists(csv_file_path):
        messages.error(request, 'Không tìm thấy dữ liệu điểm thi')
        return redirect('score-ranking')
    
    # Đọc dữ liệu từ file CSV
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader, None)  # Bỏ qua header nếu có
            count = 0
            for line in reader:
                if len(line) >= 11:  # Đảm bảo đủ cột dữ liệu
                    Candidate.objects.create(
                        sbd = line[0],
                        name = line[1],
                        birth = line[2],
                        place = line[3],
                        sex = line[4],
                        class_name = line[5],
                        school = line[6],
                        subject = line[7],
                        score = line[8],
                        rank = line[9],
                        prize = line[10],
                    )
                    count += 1
        messages.success(request, f'Đã nhập {count} thí sinh từ dữ liệu CSV vào database')
    except Exception as e:
        messages.error(request, f'Lỗi đọc dữ liệu: {str(e)}')
    
    return redirect('score-ranking')

def ScoreRanking(request):
    if request.method == 'GET':
        return render(request, 'tra-diem.html')
    elif request.method == 'POST':
        sbd = request.POST.get('sbd')
        
        # Kiểm tra xem database có dữ liệu chưa, nếu chưa thì tải từ CSV
        if Candidate.objects.count() == 0:
            # Đường dẫn đầy đủ đến file CSV
            csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'data.csv')
            
            # Kiểm tra sự tồn tại của file CSV
            if not os.path.exists(csv_file_path):
                return render(request, 'tra-diem.html', {'error': 'Không tìm thấy dữ liệu điểm thi'})
            
            # Đọc dữ liệu từ file CSV
            try:
                with open(csv_file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    next(reader, None)  # Bỏ qua header nếu có
                    
                    for line in reader:
                        if len(line) >= 11:  # Đảm bảo đủ cột dữ liệu
                            Candidate.objects.create(
                                sbd = line[0],
                                name = line[1],
                                birth = line[2],
                                place = line[3],
                                sex = line[4],
                                class_name = line[5],
                                school = line[6],
                                subject = line[7],
                                score = line[8],
                                rank = line[9],
                                prize = line[10],
                            )
            except Exception as e:
                return render(request, 'tra-diem.html', {'error': f'Lỗi đọc dữ liệu: {str(e)}'})
            
        # Tìm thí sinh theo số báo danh
        try:
            candidate = Candidate.objects.filter(sbd=sbd).first()
            if not candidate:
                return render(request, 'tra-diem.html', {'error': f'Không tìm thấy thí sinh với số báo danh {sbd}'})
                
            # Tìm điểm cao nhất của môn học
            top_score_subject = Candidate.objects.filter(subject=candidate.subject).order_by('-score').first().score
            
            # Tính phần trăm còn lại từ rank (nếu rank = 5%, thì rank_desc = 95%)
            rank_desc = 100 - int(candidate.rank) if candidate.rank and candidate.rank.isdigit() else 95
            
            # Tính vị trí thứ hạng toàn khóa
            all_candidates = Candidate.objects.count()
            better_score_all = Candidate.objects.filter(score__gt=candidate.score).count()
            rank_position = better_score_all + 1  # +1 vì thứ hạng bắt đầu từ 1
            
            #điểm trung bình môn học
            average_score_subject = Candidate.objects.filter(subject=candidate.subject).aggregate(Avg('score'))['score__avg']
            
            # Tính xếp hạng trong môn học
            candidates_same_subject = Candidate.objects.filter(subject=candidate.subject).count()
            # Đếm số thí sinh có điểm cao hơn hoặc bằng
            candidates_better_or_equal = Candidate.objects.filter(subject=candidate.subject, score__gte=candidate.score).count()
            # Lấy thứ hạng (1 là cao nhất)
            subject_rank_position = candidates_better_or_equal
            
            # Tính phần trăm top trong môn học (1% là cao nhất)
            subject_rank = max(1, min(100, round((subject_rank_position / candidates_same_subject) * 100)))
            if subject_rank_position == 1:  # Nếu là thứ hạng 1 thì luôn là top 1%
                subject_rank = 1
            
            subject_rank_desc = 100 - subject_rank  # Phần trăm còn lại cao hơn
            
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
            }
            return render(request, 'tra-diem.html', data_output)
            
        except Exception as e:
            return render(request, 'tra-diem.html', {'error': f'Lỗi xử lý dữ liệu: {str(e)}'})

def redirect_to_score_ranking(request):
    return redirect('score-ranking')
