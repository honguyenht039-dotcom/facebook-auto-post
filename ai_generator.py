import logging
from google import genai
from google.genai import types
from PIL import Image
import os

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_fb_post_content(content):
    """
    Loại bỏ triệt để các câu dẫn nhập chào hỏi của AI ở đầu bài viết (như 'Tuyệt vời! Dưới đây là...', '---')
    chỉ giữ lại nội dung bài đăng chính thức.
    """
    prefixes_to_ignore = [
        "tuyệt vời",
        "dưới đây là",
        "đây là bài đăng",
        "đây là bài viết",
        "bài đăng facebook",
        "kết nối chặt chẽ",
        "hình ảnh",
        "gợi ý bài viết",
        "bài đăng gợi ý",
        "chúc bạn",
        "hy vọng",
        "---"
    ]
    
    lines = content.split('\n')
    cleaned_lines = []
    start_adding = False
    
    # Một số emoji phổ biến thường dùng ở tiêu đề
    title_emojis = ["🌸", "🌟", "✏️", "🔥", "📢", "🔔", "👉", "⚡", "🍀", "💎", "❤️", "🎯"]
    
    for line in lines:
        stripped = line.strip()
        
        # Nếu là dòng trống
        if not stripped:
            if start_adding:
                cleaned_lines.append(line)  # Giữ lại các dòng trống ở giữa bài viết
            continue
            
        # Kiểm tra xem dòng này có chứa các từ khóa dẫn nhập của AI không
        is_intro = any(prefix in stripped.lower() for prefix in prefixes_to_ignore)
        
        # Nhận diện dòng bắt đầu tiêu đề thực tế: Thường bắt đầu bằng in đậm '**' hoặc có chứa emoji tiêu đề
        is_title_format = stripped.startswith("**") or any(emoji in stripped for emoji in title_emojis)
        
        if not start_adding:
            # Ưu tiên nhận diện tiêu đề thực tế
            if is_title_format and not is_intro:
                start_adding = True
                cleaned_lines.append(line)
            # Hoặc dòng thường không phải dẫn nhập và không phải gạch ngang phân tách
            elif not is_intro and not stripped.startswith("---") and not stripped.startswith("-"):
                start_adding = True
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines).strip()

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
        
        raw_content = response.text.strip()
        
        # Gọi hàm lọc bỏ triệt để các câu giới thiệu thừa của AI
        content = clean_fb_post_content(raw_content)
                
        logger.info("Tạo nội dung và làm sạch thành công!")
        return content
        
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {str(e)}")
        raise e
