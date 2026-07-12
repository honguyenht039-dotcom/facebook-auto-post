import logging
from google import genai
from google.genai import types
from PIL import Image
import os

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_fb_post(api_key, subject="Phong trào thi đua 3 nhất", unit="Phân trại số 1, trại giam Phú Hòa", extra_requirements="", image_path=None):
    """
    Sử dụng Gemini API để sinh nội dung bài đăng Facebook ngắn gọn, súc tích và hấp dẫn.
    Nếu có image_path, Gemini sẽ phân tích hình ảnh để viết nội dung phù hợp nhất.
    """
    if not api_key:
        raise ValueError("Gemini API Key không được để trống!")
        
    try:
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "Bạn là một chuyên gia truyền thông xã hội. Nhiệm vụ của bạn là viết một bài đăng Facebook ngắn gọn, "
            "súc tích và hấp dẫn về hoạt động thi đua, phong trào của các đơn vị."
            "\nQuy tắc viết:"
            "\n1. Nội dung cực kỳ ngắn gọn, cô đọng, dễ đọc, không rườm rà (tối đa 150-200 từ)."
            "\n2. Giọng văn trang trọng nhưng năng động, mang tính cổ vũ thi đua, tích cực."
            "\n3. Sử dụng các emoji phù hợp để bài viết trực quan."
            "\n4. Thêm các hashtag có liên quan ở cuối bài viết (ví dụ: #ThiDua, #PhanTrai1, #PhuHoa, #3Nhat...)."
            "\n5. Bố cục rõ ràng, chia dòng hợp lý để dễ theo dõi."
        )
        
        prompt = (
            f"Hãy viết một bài đăng Facebook ngắn gọn với thông tin sau:\n"
            f"- Chủ đề: {subject}\n"
            f"- Đơn vị thực hiện: {unit}\n"
        )
        
        if image_path and os.path.exists(image_path):
            prompt += "- Hãy phân tích hình ảnh đính kèm để viết nội dung bài đăng mô tả hoặc liên quan chặt chẽ tới hình ảnh này.\n"
            
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
                
        logger.info(f"Đang gọi Gemini API để tạo nội dung...")
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        
        content = response.text.strip()
        logger.info("Tạo nội dung thành công!")
        return content
        
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {str(e)}")
        raise e
