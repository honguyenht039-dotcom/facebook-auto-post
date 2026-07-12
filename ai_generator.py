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
            "\nQuy tắc viết quan trọng:"
            "\n1. CHỈ TRẢ VỀ TRỰC TIẾP NỘI DUNG BÀI ĐĂNG FACEBOOK. Tuyệt đối không thêm bất kỳ lời dẫn nhập, lời mở đầu, lời chào hỏi hoặc phần giới thiệu nào ở đầu bài viết (Ví dụ: KHÔNG viết 'Tuyệt vời! Dưới đây là...', 'Đây là bài đăng...', 'Dưới đây là nội dung...'). Bắt đầu bài viết bằng nội dung tiêu đề hoặc văn bản chính luôn."
            "\n2. Nội dung cực kỳ ngắn gọn, cô đọng, dễ đọc, không rườm rà (tối đa 150-200 từ)."
            "\n3. Giọng văn trang trọng nhưng năng động, mang tính cổ vũ thi đua, tích cực."
            "\n4. Sử dụng các emoji phù hợp để bài viết trực quan."
            "\n5. Thêm các hashtag có liên quan ở cuối bài viết (ví dụ: #ThiDua, #PhanTrai1, #PhuHoa, #3Nhat...)."
            "\n6. Bố cục rõ ràng, chia dòng hợp lý để dễ theo dõi."
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
        
        # Một số trường hợp dự phòng nếu Gemini vẫn trả về lời dẫn nhập mặc dù đã có system_instruction
        prefixes_to_remove = [
            "Tuyệt vời!",
            "Dưới đây là",
            "Đây là bài đăng",
            "Đây là bài viết",
            "Bài đăng Facebook bạn có thể sử dụng",
            "Kết hợp hình ảnh"
        ]
        
        # Loại bỏ các dòng dẫn nhập thừa nếu có
        lines = content.split('\n')
        if lines and any(any(prefix in lines[0] for prefix in prefixes_to_remove) for _ in range(1)):
            # Quét tìm dòng tiêu đề thực sự (bắt đầu bằng emoji hoặc viết hoa)
            cleaned_lines = []
            start_adding = False
            for line in lines:
                # Nếu gặp dòng trống hoặc dòng giới thiệu thì bỏ qua cho đến khi gặp tiêu đề hoặc nội dung chính
                if not start_adding:
                    if line.strip() and not any(p in line for p in prefixes_to_remove) and not line.strip().startswith("---"):
                        start_adding = True
                if start_adding:
                    cleaned_lines.append(line)
            if cleaned_lines:
                content = '\n'.join(cleaned_lines).strip()
                
        logger.info("Tạo nội dung thành công!")
        return content
        
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {str(e)}")
        raise e
