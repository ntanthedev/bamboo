import os
import logging
import json
import mimetypes
from celery import shared_task
from django.conf import settings
from .models import Document, UploadedFile, Question, Answer, Subject
import google.generativeai as genai
from google.generativeai import types

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_document(self, document_id, additional_requirements=""):
    """
    Task Celery xử lý nhiều tài liệu (PDF, TXT, Ảnh) và tạo câu hỏi
    sử dụng Gemini API qua File API.
    """
    document = None
    google_file_objects = [] 
    model = None

    try:
        api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        
        model_name = 'gemini-3-pro-preview'
        model = genai.GenerativeModel(model_name)
        
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.progress = 10
        document.progress_message = "Đang chuẩn bị xử lý tài liệu..."
        document.save()

        uploaded_files = list(document.uploaded_files.all())
        if not uploaded_files:
            raise ValueError("No files found associated with this document.")

        logger.info(f"Processing document ID {document_id} ({document.title}) with {len(uploaded_files)} files.")

        uploaded_google_files = []
        total_files = len(uploaded_files)
        
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
                mime_type, _ = mimetypes.guess_type(file_path)
                file_extension = os.path.splitext(file_path)[1].lower()

                if file_extension == '.jfif':
                    mime_type = 'image/jpeg'
                    logger.info(f"Detected .jfif extension, forcing mime_type to {mime_type}")
                elif not mime_type:
                    mime_type = 'application/octet-stream'
                    logger.warning(f"Could not guess mime type for {file_path}, using default: {mime_type}")
                else:
                     logger.info(f"Guessed mime type for {file_path}: {mime_type}")

                google_file = genai.upload_file(
                    path=file_path,
                    mime_type=mime_type
                )
                google_file_objects.append(google_file)
                uploaded_google_files.append(google_file)
                logger.info(f"Successfully uploaded {google_file.name} ({google_file.mime_type})")
                
                progress = 20 + int(30 * (i + 1) / total_files)
                document.progress = progress
                document.progress_message = f"Đã tải lên {i+1}/{total_files} tệp tài liệu..."
                document.save()
                
            except Exception as upload_error:
                logger.error(f"Failed to upload file {file_path}: {upload_error}")
                document.error_message = f"Không thể tải lên tệp: {os.path.basename(file_path)}"
                document.save()
        
        if not uploaded_google_files:
             raise ValueError("No files could be successfully uploaded to Google File API.")

        subject_name = document.subject.name if document.subject else document.subject_text
        logger.info(f"Generating questions for document {document_id} using {len(uploaded_google_files)} files.")
        
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
            raise ValueError("Failed to generate questions from the provided files.")

        document.progress = 80
        document.progress_message = f"Đã tạo {len(questions_data)} câu hỏi. Đang lưu vào cơ sở dữ liệu..."
        document.save()

        logger.info(f"Saving {len(questions_data)} questions to database for document {document_id}.")
        Question.objects.filter(document=document).delete()
        
        questions_saved = 0
        total_questions = len(questions_data)
        
        for i, q_data in enumerate(questions_data):
            if not all(k in q_data for k in ('question', 'answers')) or not isinstance(q_data['answers'], list):
                 logger.warning(f"Skipping invalid question data structure: {q_data}")
                 continue
                 
            question_text = q_data['question']
            difficulty = q_data.get('difficulty', 'medium').lower()
            if difficulty not in ['easy', 'medium', 'hard']:
                 difficulty = 'medium'
            
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
                explanation = ans_data.get('explanation') if is_correct else None
                
                if is_correct:
                    has_correct_answer = True
                
                Answer.objects.create(
                    question=question,
                    text=ans_data['text'],
                    is_correct=is_correct,
                    explanation=explanation,
                    position=j
                )
                answers_saved_count += 1
            
            if answers_saved_count == 0 or not has_correct_answer:
                logger.warning(f"Question '{question_text[:50]}...' saved without valid answers or no correct answer marked. Deleting question.")
                question.delete()
            else:
                questions_saved += 1
                
            if i % 5 == 0 or i == total_questions - 1:
                progress = 80 + int(15 * (i + 1) / total_questions) 
                document.progress = progress
                document.progress_message = f"Đang lưu câu hỏi {i+1}/{total_questions}..."
                document.save()

        document.status = 'completed'
        document.progress = 100
        document.progress_message = f"Hoàn thành! Đã tạo {questions_saved} câu hỏi."
        document.error_message = None
        document.save()
        logger.info(f"Successfully processed document {document_id}.")
        
    except Document.DoesNotExist:
        logger.error(f'Document with id {document_id} does not exist')
    except Exception as e:
        logger.exception(f'Error processing document {document_id}: {str(e)}')
        if document:
            document.status = 'failed'
            document.progress = 0
            if not document.error_message or isinstance(e, ValueError):
                 document.error_message = f"Lỗi xử lý: {str(e)}"
            document.save()
    finally:
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
        prompt_text = f"""
        Dựa vào nội dung các tài liệu được cung cấp, hãy lấy toàn bộ câu hỏi trắc nghiệm về môn học '{subject}'.

        Mỗi câu hỏi cần có 4 đáp án, trong đó **chỉ có 1 đáp án đúng**. Hãy cố gắng tạo các đáp án sai hợp lý và gần giống đáp án đúng.
Phân loại độ khó của mỗi câu hỏi là 'easy', 'medium', hoặc 'hard'.
        **Quan trọng: Với mỗi câu hỏi, hãy cung cấp một lời giải thích ngắn gọn nhưng mà phải chi tiết cho đáp án vì sao đúng vì sao sai trong trường 'explanation'.**

{f'Yêu cầu bổ sung từ người dùng: {requirements}' if requirements else ''}

    Tuyệt đối lưu ý:
        - Chỉ trả về mảng JSON, không bao gồm bất kỳ văn bản giải thích nào khác.
        - Không sử dụng markdown code block (```json ... ```).
        - Đảm bảo trường 'explanation' chỉ có ở đáp án đúng (is_correct: true).

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
        """

        request_content = [prompt_text]
        for f in uploaded_files:
            request_content.append(f)

        logger.info(f"Sending generation request to Gemini with {len(uploaded_files)} files.")
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json",max_output_tokens=80000)

        response = model.generate_content(
            request_content,
        )

        if not response.parts:
             logger.error("Gemini response did not contain any parts.")
             try:
                 logger.warning(f"Prompt Feedback: {response.prompt_feedback}")
             except Exception:
                 pass
             return None
        
        response_text = response.text

        logger.debug(f"Raw response from Gemini: {response_text[:500]}...")
        if "```json" in response_text:
            response_text = response_text.split("```json")[1]
            response_text = response_text.split("```")[0]
            response_text = response_text.strip()
        questions_data = json.loads(response_text)
        
        if not isinstance(questions_data, list):
            logger.error(f"Parsed JSON is not a list: {type(questions_data)}")
            return None
        
        logger.info(f"Successfully generated and parsed {len(questions_data)} questions.")
        return questions_data

    except types.BlockedPromptException as bpe:
        logger.error(f"Prompt blocked by API safety settings: {bpe}")
        return None
    except types.StopCandidateException as sce:
        logger.error(f"Generation stopped unexpectedly: {sce}")
        return None
    except json.JSONDecodeError as jde:
        logger.error(f"Failed to decode JSON response: {jde}")
        logger.error(f"Invalid JSON received: {response_text[:1000]}...")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred during question generation: {e}")
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