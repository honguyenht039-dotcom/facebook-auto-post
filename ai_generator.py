import logging
from google import genai
from google.genai import types
from PIL import Image
import os
import json
from pydantic import BaseModel, Field

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Định nghĩa cấu trúc đầu ra bắt buộc của bài đăng Facebook
class FacebookPostSchema(BaseModel):
    title: str = Field(description="Tiêu đề của bài đăng Facebook, bắt đầu bằng emoji phù hợp và viết hoa nổi bật (Ví dụ: '🌸 TINH THẦN \"3 NHẤT\" NỞ RỘ!')")
    body: str = Field(description="Nội dung chính của bài đăng. Ngắn gọn, súc tích, truyền cảm hứng và chia dòng hợp lý bằng emoji (tối đa 150 từ).")
    hashtags: str = Field(description="Danh sách 5-7 hashtag liên quan cách nhau bằng khoảng trắng (Ví dụ: '#ThiDua3Nhat #PhanTrai1 #TrạiGiamPhuHoa')")

def generate_fb_post(api_key, subject="Phong trào thi đua 3 nhất", unit="Phân trại số 1, trại giam Phú Hòa", extra_requirements="", image_path=None):
    """
    Sử dụng Gemini API với cấu trúc đầu ra JSON (Structured Outputs) để đảm bảo 100% 
    không có bất kỳ câu dẫn nhập thừa nào từ AI.
    """
    if not api_key:
        raise ValueError("Gemini API Key không được để trống!")
        
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Hãy viết một bài đăng Facebook ngắn gọn về:\n"
            f"- Chủ đề: {subject}\n"
            f"- Đơn vị thực hiện: {unit}\n"
        )
        
        if image_path and os.path.exists(image_path):
            prompt += "- Hãy phân tích hình ảnh đính kèm để viết nội dung mô tả hoặc liên quan chặt chẽ tới hình ảnh này.\n"
            
        if extra_requirements:
            prompt += f"- Yêu cầu thêm từ người dùng: {extra_requirements}\n"
            
        contents = [prompt]
        
        # Nếu có ảnh, nạp ảnh vào Gemini
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                contents.append(img)
                logger.info(f"Đã nạp hình ảnh từ {image_path} vào Gemini...")
            except Exception as img_err:
                logger.error(f"Không thể mở ảnh bằng PIL: {str(img_err)}")
                
        logger.info(f"Đang gọi Gemini API với cấu trúc JSON định dạng trước...")
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FacebookPostSchema,
                temperature=0.7,
            )
        )
        
        # Parse JSON đầu ra từ Gemini
        post_json = json.loads(response.text)
        
        title = post_json.get("title", "").strip()
        body = post_json.get("body", "").strip()
        hashtags = post_json.get("hashtags", "").strip()
        
        # Tạo định dạng bài đăng Facebook hoàn chỉnh
        # Tiêu đề in đậm kèm dòng kẻ phân cách nhẹ nhàng
        formatted_content = f"**{title}**\n\n{body}\n\n{hashtags}"
        
        logger.info("Tạo nội dung Structured Output thành công!")
        return formatted_content
        
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {str(e)}")
        raise e
