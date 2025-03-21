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
