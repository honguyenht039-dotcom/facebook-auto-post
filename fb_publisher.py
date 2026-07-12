import requests
import os
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def publish_to_facebook(page_id, page_token, message, image_path=None):
    """
    Đăng bài viết lên Facebook Fanpage.
    - Nếu có image_path: Đăng ảnh kèm caption lên endpoint /{page_id}/photos
    - Nếu không có image_path: Đăng bài viết thuần văn bản lên endpoint /{page_id}/feed
    """
    if not page_id or not page_token:
        raise ValueError("Facebook Page ID và Page Access Token không được để trống!")
        
    if not message:
        raise ValueError("Nội dung bài đăng không được để trống!")

    # Cắt khoảng trắng đầu cuối
    message = message.strip()
    
    # Sử dụng Graph API v20.0
    api_version = "v20.0"
    
    if image_path and os.path.exists(image_path):
        # Đăng bài viết kèm hình ảnh
        url = f"https://graph.facebook.com/{api_version}/{page_id}/photos"
        payload = {
            'caption': message,
            'access_token': page_token
        }
        
        logger.info(f"Đang chuẩn bị đăng ảnh: {image_path} kèm bài viết lên Page {page_id}...")
        
        try:
            with open(image_path, 'rb') as img_file:
                files = {
                    'source': img_file
                }
                response = requests.post(url, data=payload, files=files)
                result = response.json()
                
                if response.status_code == 200:
                    fb_id = result.get('post_id') or result.get('id')
                    logger.info(f"Đăng bài viết kèm ảnh thành công! FB ID: {fb_id}")
                    return fb_id
                else:
                    error_msg = result.get('error', {}).get('message', 'Lỗi không xác định từ Facebook')
                    logger.error(f"Lỗi Facebook API (đăng ảnh): {error_msg}")
                    raise Exception(f"Facebook API Error: {error_msg}")
                    
        except Exception as e:
            logger.error(f"Lỗi khi gửi ảnh lên Facebook: {str(e)}")
            raise e
    else:
        # Đăng bài viết thuần văn bản
        url = f"https://graph.facebook.com/{api_version}/{page_id}/feed"
        payload = {
            'message': message,
            'access_token': page_token
        }
        
        logger.info(f"Đang chuẩn bị đăng bài viết thuần văn bản lên Page {page_id}...")
        
        try:
            response = requests.post(url, data=payload)
            result = response.json()
            
            if response.status_code == 200:
                fb_id = result.get('id')
                logger.info(f"Đăng bài viết thuần văn bản thành công! FB ID: {fb_id}")
                return fb_id
            else:
                error_msg = result.get('error', {}).get('message', 'Lỗi không xác định từ Facebook')
                logger.error(f"Lỗi Facebook API (đăng text): {error_msg}")
                raise Exception(f"Facebook API Error: {error_msg}")
                
        except Exception as e:
            logger.error(f"Lỗi khi đăng bài viết lên Facebook: {str(e)}")
            raise e
