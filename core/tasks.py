import os
# import PyPDF2 # Không còn sử dụng
import logging
import json
from celery import shared_task
from django.conf import settings
from .models import Document, UploadedFile, Question, Answer, Subject
import google.generativeai as genai
from google.generativeai import types

# Cấu hình logging
logger = logging.getLogger(__name__)

# Cấu hình Client Gemini (nên dùng Client thay vì configure toàn cục)
# api_key nên được lấy từ settings hoặc biến môi trường khi khởi tạo client

@shared_task(bind=True)
def process_document(self, document_id, additional_requirements=""):
    """
    Task Celery xử lý nhiều tài liệu (PDF, TXT, Ảnh) và tạo câu hỏi
    sử dụng Gemini API qua File API.
    """
    document = None
    google_file_objects = [] # Lưu các đối tượng file từ Google để xóa sau
    model = None

    try:
        # Khởi tạo Client với API Key
        api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        
        # Tạo model Gemini
        model_name = 'gemini-2.5-pro-exp-03-25' # Hoặc model khác phù hợp
        model = genai.GenerativeModel(model_name)
        
        # 1. Lấy thông tin Document và các UploadedFile
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.progress = 10
        document.progress_message = "Đang chuẩn bị xử lý tài liệu..."
        document.save()

        uploaded_files = list(document.uploaded_files.all()) # Lấy danh sách file từ model mới
        if not uploaded_files:
            raise ValueError("No files found associated with this document.")

        logger.info(f"Processing document ID {document_id} ({document.title}) with {len(uploaded_files)} files.")

        # 2. Upload các file lên Google File API
        uploaded_google_files = []
        total_files = len(uploaded_files)
        
        # Cập nhật tiến trình
        document.progress = 20
        document.progress_message = f"Đang tải lên {total_files} tệp tài liệu..."
        document.save()
        
        for i, uf in enumerate(uploaded_files):
            file_path = uf.file.path
            if not os.path.exists(file_path):
                logger.warning(f"File path not found: {file_path} for UploadedFile ID {uf.id}. Skipping.")
                continue
            
            logger.info(f"Uploading file {uf.id} ({os.path.basename(file_path)}) to Google File API...")
            try:
                # Upload file
                google_file = genai.upload_file(path=file_path)
                google_file_objects.append(google_file) # Lưu lại để xóa sau
                uploaded_google_files.append(google_file)
                logger.info(f"Successfully uploaded {google_file.name} ({google_file.mime_type})")
                
                # Cập nhật tiến trình upload
                progress = 20 + int(30 * (i + 1) / total_files)  # Từ 20% đến 50%
                document.progress = progress
                document.progress_message = f"Đã tải lên {i+1}/{total_files} tệp tài liệu..."
                document.save()
                
            except Exception as upload_error:
                logger.error(f"Failed to upload file {file_path}: {upload_error}")
                # Bỏ qua và tiếp tục với các file khác
                document.error_message = f"Không thể tải lên tệp: {os.path.basename(file_path)}"
                document.save()
        
        # Nếu không upload được file nào lên google thì dừng
        if not uploaded_google_files:
             raise ValueError("No files could be successfully uploaded to Google File API.")

        # 3. Gọi Gemini API để tạo câu hỏi
        subject_name = document.subject.name if document.subject else document.subject_text
        logger.info(f"Generating questions for document {document_id} using {len(uploaded_google_files)} files.")
        
        # Cập nhật tiến trình
        document.progress = 50
        document.progress_message = "Đang tạo câu hỏi từ tài liệu sử dụng AI..."
        document.save()
        
        questions_data = generate_questions_from_files(
            model=model,
            uploaded_files=uploaded_google_files,
            subject=subject_name,
            requirements=additional_requirements
        )
        
        if not questions_data:
            # Lỗi đã được log bên trong hàm con
            raise ValueError("Failed to generate questions from the provided files.")

        # Cập nhật tiến trình
        document.progress = 80
        document.progress_message = f"Đã tạo {len(questions_data)} câu hỏi. Đang lưu vào cơ sở dữ liệu..."
        document.save()

        # 4. Lưu câu hỏi và đáp án
        logger.info(f"Saving {len(questions_data)} questions to database for document {document_id}.")
        Question.objects.filter(document=document).delete() # Xóa câu hỏi cũ nếu chạy lại task
        
        questions_saved = 0
        total_questions = len(questions_data)
        
        for i, q_data in enumerate(questions_data):
            # Validate cấu trúc dữ liệu q_data cơ bản
            if not all(k in q_data for k in ('question', 'answers')) or not isinstance(q_data['answers'], list):
                 logger.warning(f"Skipping invalid question data structure: {q_data}")
                 continue
                 
            question_text = q_data['question']
            difficulty = q_data.get('difficulty', 'medium').lower()
            if difficulty not in ['easy', 'medium', 'hard']:
                 difficulty = 'medium' # Default nếu giá trị không hợp lệ
            
            # Đảm bảo có đối tượng Subject hợp lệ
            if document.subject:
                subject = document.subject
            else:
                subject = Subject.objects.get_or_create(name=subject_name)
                 
            question = Question.objects.create(
                text=question_text,
                subject=subject,
                difficulty=difficulty,
                document=document
            )
            
            answers_saved_count = 0
            has_correct_answer = False
            for j, ans_data in enumerate(q_data['answers']):
                if not isinstance(ans_data, dict) or 'text' not in ans_data or 'is_correct' not in ans_data:
                    logger.warning(f"Skipping invalid answer data structure for question '{question_text[:50]}...': {ans_data}")
                    continue
                
                is_correct = ans_data['is_correct']
                explanation = ans_data.get('explanation') if is_correct else None # Lấy explanation nếu là đáp án đúng
                
                if is_correct:
                    has_correct_answer = True
                
                Answer.objects.create(
                    question=question,
                    text=ans_data['text'],
                    is_correct=is_correct,
                    explanation=explanation, # Lưu explanation
                    position=j
                )
                answers_saved_count += 1
            
            # Kiểm tra xem có lưu được đáp án và có ít nhất 1 đáp án đúng không
            if answers_saved_count == 0 or not has_correct_answer:
                logger.warning(f"Question '{question_text[:50]}...' saved without valid answers or no correct answer marked. Deleting question.")
                question.delete() # Xóa câu hỏi nếu không có đáp án hợp lệ
            else:
                questions_saved += 1
                
            # Cập nhật tiến trình lưu câu hỏi
            if i % 5 == 0 or i == total_questions - 1:  # Cập nhật sau mỗi 5 câu hỏi để tránh quá nhiều thao tác DB
                progress = 80 + int(15 * (i + 1) / total_questions)  # Từ 80% đến 95%
                document.progress = progress
                document.progress_message = f"Đang lưu câu hỏi {i+1}/{total_questions}..."
                document.save()

        # 5. Cập nhật trạng thái thành công
        document.status = 'completed'
        document.progress = 100
        document.progress_message = f"Hoàn thành! Đã tạo {questions_saved} câu hỏi."
        document.error_message = None # Xóa lỗi cũ nếu thành công
        document.save()
        logger.info(f"Successfully processed document {document_id}.")
        
    except Document.DoesNotExist:
        logger.error(f'Document with id {document_id} does not exist')
    except Exception as e:
        logger.exception(f'Error processing document {document_id}: {str(e)}') # Dùng exception để log cả traceback
        if document: # Cập nhật trạng thái lỗi nếu lấy được document
            document.status = 'failed'
            document.progress = 0
            # Ưu tiên giữ lỗi cụ thể nếu có, nếu không ghi lỗi chung
            if not document.error_message or isinstance(e, ValueError):
                 document.error_message = f"Lỗi xử lý: {str(e)}"
            document.save()
    finally:
        # 6. Xóa các file đã tải lên Google File API
        if google_file_objects:
            if document and document.status != 'failed':
                document.progress = 95
                document.progress_message = "Đang dọn dẹp tệp tạm..."
                document.save()
                
            logger.info(f"Cleaning up {len(google_file_objects)} uploaded files from Google File API...")
            for google_file in google_file_objects:
                try:
                    logger.debug(f"Deleting file: {google_file.name}")
                    genai.delete_file(name=google_file.name)
                except Exception as delete_error:
                    # Chỉ log lỗi, không nên dừng cả task
                    logger.error(f"Failed to delete Google File API file {google_file.name}: {delete_error}")

            if document and document.status == 'completed':
                document.progress = 100
                document.save()

def generate_questions_from_files(model, uploaded_files, subject, requirements):
    """
    Sử dụng Gemini API để tạo câu hỏi từ danh sách các file đã upload.
    Trả về list các dictionaries câu hỏi hoặc None nếu lỗi.
    """
    try:
        # Xây dựng prompt
        prompt_text = f"""
        Dựa vào nội dung các tài liệu được cung cấp, hãy lấy toàn bộ câu hỏi trắc nghiệm về môn học '{subject}'.

        Mỗi câu hỏi cần có 4 đáp án, trong đó **chỉ có 1 đáp án đúng**. Hãy cố gắng tạo các đáp án sai hợp lý và gần giống đáp án đúng.
Phân loại độ khó của mỗi câu hỏi là 'easy', 'medium', hoặc 'hard'.
        **Quan trọng: Với mỗi câu hỏi, hãy cung cấp một lời giải thích ngắn gọn nhưng mà phải chi tiết cho đáp án vì sao đúng vì sao sai trong trường 'explanation'.**

{f'Yêu cầu bổ sung từ người dùng: {requirements}' if requirements else ''}

        Hãy trả về kết quả dưới dạng một mảng JSON hợp lệ duy nhất theo cấu trúc ví dụ sau:
[
    {{
        "question": "Nội dung câu hỏi ở đây...",
        "difficulty": "medium",
        "answers": [
                    {{"text": "Nội dung đáp án A", "is_correct": false, "explanation": "Lời giải thích ngắn gọn vì sao đáp án A sai."}},
                    {{"text": "Nội dung đáp án B", "is_correct": true, "explanation": "Lời giải thích ngắn gọn vì sao đáp án B đúng."}},
                    {{"text": "Nội dung đáp án C", "is_correct": false, "explanation": "Lời giải thích ngắn gọn vì sao đáp án C sai."}},
                    {{"text": "Nội dung đáp án D", "is_correct": false, "explanation": "Lời giải thích ngắn gọn vì sao đáp án D sai."}}
                ]
            }},
            // ... các câu hỏi khác (cũng bao gồm explanation cho đáp án đúng) ...
        ]

        Lưu ý:
        - Chỉ trả về mảng JSON, không bao gồm bất kỳ văn bản giải thích nào khác.
        - Không sử dụng markdown code block (```json ... ```).
        - Đảm bảo trường 'explanation' chỉ có ở đáp án đúng (is_correct: true).
        """

        # Tạo nội dung yêu cầu (Kết hợp prompt và các file đã upload)
        request_content = [prompt_text]
        for f in uploaded_files:
            request_content.append(f) # Thêm các đối tượng file đã upload

        logger.info(f"Sending generation request to Gemini with {len(uploaded_files)} files.")
        # Cấu hình để trả về JSON
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")

        # Gọi API
        response = model.generate_content(
            request_content,
            generation_config=generation_config,
            # Cân nhắc thêm safety_settings nếu cần
            # safety_settings=[...]
        )

        # Kiểm tra xem response có chứa text không
        if not response.parts:
             logger.error("Gemini response did not contain any parts.")
             try:
                 logger.warning(f"Prompt Feedback: {response.prompt_feedback}")
             except Exception:
                 pass
             return None
        
        # Lấy phần text từ response (đối với JSON response)
        response_text = response.text

        # Parse JSON
        logger.debug(f"Raw response from Gemini: {response_text[:500]}...") # Log một phần response để debug
        questions_data = json.loads(response_text)
        
        # Kiểm tra kiểu dữ liệu trả về
        if not isinstance(questions_data, list):
            logger.error(f"Parsed JSON is not a list: {type(questions_data)}")
            return None
        
        logger.info(f"Successfully generated and parsed {len(questions_data)} questions.")
        return questions_data

    except types.BlockedPromptException as bpe:
        logger.error(f"Prompt blocked by API safety settings: {bpe}")
        # Có thể lưu thông tin lỗi này vào Document.error_message
        return None
    except types.StopCandidateException as sce:
        logger.error(f"Generation stopped unexpectedly: {sce}")
        return None
    except json.JSONDecodeError as jde:
        logger.error(f"Failed to decode JSON response: {jde}")
        logger.error(f"Invalid JSON received: {response_text[:1000]}...") # Log nhiều hơn để xem lỗi JSON
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred during question generation: {e}") # Log cả traceback
        return None

# --- Xóa hàm cũ không còn sử dụng --- 
# def generate_questions_with_gemini(file_path, subject):
#    pass

# --- Các hàm extract_text không còn sử dụng --- 
# def extract_text_from_document(file_path):
#     ...
# def extract_text_from_pdf(pdf_path):
#     ...

# def generate_questions_with_gemini(file_path, subject):
#     """
#     Sử dụng Gemini API để tạo câu hỏi trắc nghiệm bằng cách tải file trực tiếp.
#     Trả về tuple (questions_data, uploaded_file_resource) hoặc (None, None) nếu lỗi.
#     """
#     uploaded_file = None
#     try:
#         logger.info(f"Uploading file to Gemini: {file_path}")
#         # Tải file lên Gemini API
#         # display_name giúp dễ nhận biết file trong File API nếu cần
#         uploaded_file = genai.upload_file(path=file_path, display_name=os.path.basename(file_path))
#         logger.info(f"Successfully uploaded file: {uploaded_file.uri} (Name: {uploaded_file.name})")
#
#         # Tạo prompt cho Gemini, yêu cầu phân tích file được cung cấp
#         prompt = f"""
#         Hãy phân tích tệp được cung cấp ({uploaded_file.display_name}) và tìm câu hỏi trắc nghiệm dựa trên nội dung của nó. Môn học: {subject}.
#         
#         Mỗi câu hỏi cần có 4 đáp án (A, B, C, D), trong đó chỉ có 1 đáp án đúng.
#         Hãy trả về kết quả dưới định dạng JSON như sau:
#         [
#             {{
#                 "question": "Nội dung câu hỏi",
#                 "difficulty": "easy|medium|hard",
#                 "answers": [
#                     {{"text": "Đáp án A", "is_correct": false}},
#                     {{"text": "Đáp án B", "is_correct": true}},
#                     {{"text": "Đáp án C", "is_correct": false}},
#                     {{"text": "Đáp án D", "is_correct": false}}
#                 ]
#             }},
#             ...
#         ]
#         
#         Chỉ trả về duy nhất mảng JSON hợp lệ, không thêm văn bản giải thích nào khác.
#         """
#         
#         # Chọn model hỗ trợ file input (ví dụ: gemini-1.5-pro-latest)
#         model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
#         
#         # Gọi Gemini API với prompt và file đã tải lên
#         logger.info(f"Generating content using model {model.model_name} with file {uploaded_file.name}")
#         response = model.generate_content([prompt, uploaded_file])
#         
#         # Phân tích kết quả JSON
#         import json
#         response_text = response.text
#         logger.debug(f"Gemini response text: {response_text}") # Log full response for debugging
#         
#         # Cố gắng tìm và parse JSON từ response
#         json_start = response_text.find('[')
#         json_end = response_text.rfind(']')
#         if json_start != -1 and json_end != -1:
#             json_str = response_text[json_start:json_end+1]
#             try:
#                 questions = json.loads(json_str)
#                 logger.info(f"Successfully parsed {len(questions)} questions from Gemini response.")
#                 return questions, uploaded_file # Trả về cả questions và file resource để xóa sau
#             except json.JSONDecodeError as json_error:
#                 logger.error(f'JSONDecodeError parsing Gemini response: {json_error}. Response text: {response_text}')
#                 raise ValueError(f"Không thể phân tích JSON từ phản hồi của API: {json_error}")
#         else:
#             logger.error(f'Could not find valid JSON array in Gemini response: {response_text}')
#             raise ValueError("Phản hồi từ API không chứa định dạng JSON mong đợi.")
#
#     except Exception as e:
#         logger.error(f'Error generating questions with Gemini for file {file_path}: {str(e)}')
#         # Cập nhật lỗi vào document nếu có thể (task cha sẽ làm việc này)
#         # Trả về None để báo hiệu lỗi, và trả về uploaded_file nếu nó đã được tạo để có thể xóa
#         return None, uploaded_file 