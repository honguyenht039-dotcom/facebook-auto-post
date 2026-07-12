import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
import threading
import logging
import os
import time

# Import các module dự án
import database
import fb_publisher
import ai_generator

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thư mục lưu ảnh tải từ Telegram
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Biến toàn cục quản lý Bot và Thread
bot_instance = None
polling_thread = None
stop_event = threading.Event()

def send_post_to_telegram(post_id):
    """
    Gửi bài viết cần duyệt sang Telegram Chat ID của người dùng.
    """
    post = database.get_post(post_id)
    if not post:
        raise ValueError(f"Không tìm thấy bài viết với ID: {post_id}")
        
    token = database.get_setting("tg_bot_token")
    chat_id = database.get_setting("tg_chat_id")
    
    if not token or not chat_id:
        raise ValueError("Vui lòng cấu hình đầy đủ Telegram Bot Token và Chat ID trong Cài đặt!")
        
    bot = telebot.TeleBot(token)
    
    # Tạo nút bấm inline duyệt bài
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Duyệt đăng", callback_data=f"approve:{post_id}"),
        InlineKeyboardButton("✏️ Sửa nội dung", callback_data=f"edit_req:{post_id}")
    )
    markup.add(
        InlineKeyboardButton("❌ Hủy bỏ", callback_data=f"reject:{post_id}")
    )
    
    caption = f"📝 **BÀI VIẾT CHỜ DUYỆT (ID: {post_id})**\n\n{post['content']}"
    
    # Gửi kèm ảnh nếu có
    if post['image_path'] and os.path.exists(post['image_path']):
        with open(post['image_path'], 'rb') as photo:
            msg = bot.send_photo(chat_id, photo, caption=caption[:1024], reply_markup=markup, parse_mode="Markdown")
    else:
        msg = bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="Markdown")
        
    # Cập nhật ID tin nhắn duyệt vào cơ sở dữ liệu
    database.update_post(post_id, tg_message_id=msg.message_id)
    logger.info(f"Đã gửi bài viết ID {post_id} sang Telegram duyệt. Msg ID: {msg.message_id}")
    return msg.message_id


def setup_bot_handlers(bot):
    """
    Đăng ký các xử lý sự kiện nút bấm và phản hồi tin nhắn của Bot.
    """
    
    # Handler xử lý khi người dùng gửi HÌNH ẢNH trực tiếp qua Telegram
    @bot.message_handler(content_types=['photo'])
    def handle_photo_upload(message):
        chat_id = str(message.chat.id)
        config_chat_id = database.get_setting("tg_chat_id")
        
        # Chỉ xử lý ảnh từ đúng chủ tài khoản đã cấu hình để tránh spam
        if not config_chat_id or chat_id != str(config_chat_id):
            logger.warning(f"Nhận ảnh từ Chat ID lạ ({chat_id}). Bỏ qua.")
            return
            
        bot.send_message(chat_id, "📥 **Đã nhận được ảnh của bạn!**\nĐang gửi ảnh sang AI (Gemini) để phân tích và soạn thảo bài viết. Vui lòng chờ vài giây...")
        
        try:
            # 1. Tải ảnh từ Telegram Server về máy cục bộ
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Đặt tên file theo thời gian
            file_ext = os.path.splitext(file_info.file_path)[1] or ".jpg"
            local_filename = f"tg_photo_{int(time.time())}{file_ext}"
            local_image_path = os.path.join(UPLOAD_DIR, local_filename)
            
            with open(local_image_path, 'wb') as f:
                f.write(downloaded_file)
                
            # 2. Gọi Gemini để tạo bài đăng kết hợp mô tả ảnh
            gemini_key = database.get_setting("gemini_api_key")
            if not gemini_key:
                bot.send_message(chat_id, "⚠️ Lỗi: Chưa cấu hình Gemini API Key trên giao diện Web!")
                return
                
            # Sinh nội dung tự động dựa trên thông tin mặc định
            draft_content = ai_generator.generate_fb_post(
                api_key=gemini_key,
                subject="Phong trào thi đua 3 nhất",
                unit="Phân trại số 1, trại giam Phú Hòa",
                extra_requirements="nội dung ngắn gọn, súc tích, chia bố cục rõ ràng, có emoji",
                image_path=local_image_path
            )
            
            # 3. Tạo bài đăng mới trong Database (trạng thái pending)
            post_id = database.create_post(
                content=draft_content,
                image_path=local_image_path,
                status='pending'
            )
            
            # 4. Gửi lại giao diện duyệt bài kèm các nút bấm
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Duyệt đăng", callback_data=f"approve:{post_id}"),
                InlineKeyboardButton("✏️ Sửa nội dung", callback_data=f"edit_req:{post_id}")
            )
            markup.add(
                InlineKeyboardButton("❌ Hủy bỏ", callback_data=f"reject:{post_id}")
            )
            
            caption = f"📝 **BÀI VIẾT ĐÃ TẠO TỪ ẢNH (ID: {post_id})**\n\n{draft_content}"
            
            with open(local_image_path, 'rb') as photo:
                msg = bot.send_photo(chat_id, photo, caption=caption[:1024], reply_markup=markup, parse_mode="Markdown")
                
            database.update_post(post_id, tg_message_id=msg.message_id)
            logger.info(f"Đã tạo bài viết ID {post_id} thành công từ ảnh gửi qua Telegram. Msg ID: {msg.message_id}")
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý ảnh gửi qua Telegram: {str(e)}")
            bot.send_message(chat_id, f"❌ Có lỗi xảy ra trong quá trình xử lý ảnh và gọi AI: {str(e)}")

    @bot.callback_query_handler(func=lambda call: True)
    def handle_query(call):
        data = call.data
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        if ":" not in data:
            return
            
        action, post_id_str = data.split(":")
        post_id = int(post_id_str)
        post = database.get_post(post_id)
        
        if not post:
            bot.answer_callback_query(call.id, "Lỗi: Không tìm thấy bài viết!")
            return
            
        if action == "approve":
            bot.answer_callback_query(call.id, "Đang đăng bài viết lên Facebook...")
            
            # Đọc API Facebook
            page_id = database.get_setting("fb_page_id")
            page_token = database.get_setting("fb_page_token")
            
            if not page_id or not page_token:
                bot.send_message(chat_id, "❌ Lỗi: Chưa cấu hình thông tin Facebook Page ID hoặc Access Token!")
                return
                
            try:
                # Đăng bài
                fb_post_id = fb_publisher.publish_to_facebook(
                    page_id=page_id,
                    page_token=page_token,
                    message=post['content'],
                    image_path=post['image_path']
                )
                
                # Cập nhật Database
                database.update_post(post_id, status="posted", fb_post_id=fb_post_id, error_message=None)
                
                # Sửa lại tin nhắn duyệt trên Telegram để báo thành công
                new_caption = f"✅ **ĐÃ ĐĂNG LÊN FACEBOOK THÀNH CÔNG**\n\n🔗 **ID Bài viết**: `{fb_post_id}`\n\n{post['content']}"
                
                if post['image_path'] and os.path.exists(post['image_path']):
                    bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=new_caption[:1024], reply_markup=None, parse_mode="Markdown")
                else:
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_caption, reply_markup=None, parse_mode="Markdown")
                    
                bot.send_message(chat_id, f"🎉 Đăng bài viết ID {post_id} lên Facebook thành công!")
                
            except Exception as e:
                # Cập nhật trạng thái lỗi
                database.update_post(post_id, status="error", error_message=str(e))
                
                # Hiển thị nút "Thử lại" và "Sửa" khi có lỗi
                retry_markup = InlineKeyboardMarkup()
                retry_markup.add(
                    InlineKeyboardButton("🔄 Thử đăng lại", callback_data=f"approve:{post_id}"),
                    InlineKeyboardButton("✏️ Sửa nội dung", callback_data=f"edit_req:{post_id}")
                )
                retry_markup.add(
                    InlineKeyboardButton("❌ Hủy bỏ", callback_data=f"reject:{post_id}")
                )
                
                err_caption = f"❌ **ĐĂNG LÊN FACEBOOK THẤT BẠI**\n⚠️ **Lỗi**: {str(e)}\n\n{post['content']}"
                
                try:
                    if post['image_path'] and os.path.exists(post['image_path']):
                        bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=err_caption[:1024], reply_markup=retry_markup, parse_mode="Markdown")
                    else:
                        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=err_caption, reply_markup=retry_markup, parse_mode="Markdown")
                except Exception as edit_err:
                    logger.error(f"Lỗi khi cập nhật tin nhắn lỗi Telegram: {str(edit_err)}")
                    
        elif action == "reject":
            database.update_post(post_id, status="rejected")
            bot.answer_callback_query(call.id, "Đã hủy bỏ bài viết.")
            
            new_caption = f"❌ **ĐÃ HỦY BỎ BÀI VIẾT**\n\n{post['content']}"
            if post['image_path'] and os.path.exists(post['image_path']):
                bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=new_caption[:1024], reply_markup=None, parse_mode="Markdown")
            else:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_caption, reply_markup=None, parse_mode="Markdown")
                
        elif action == "edit_req":
            bot.answer_callback_query(call.id, "Hãy nhập nội dung mới")
            # Gửi tin nhắn Force Reply yêu cầu nhập nội dung
            bot.send_message(
                chat_id,
                f"✏️ **YÊU CẦU SỬA BÀI VIẾT (ID: {post_id})**\n\nHãy **Phản hồi (Reply)** trực tiếp tin nhắn này để viết nội dung mới.",
                reply_markup=ForceReply(selective=True)
            )

    @bot.message_handler(func=lambda msg: msg.reply_to_message is not None)
    def handle_reply_message(message):
        reply_to = message.reply_to_message
        reply_to_text = reply_to.text or ""
        
        if "YÊU CẦU SỬA BÀI VIẾT (ID:" not in reply_to_text:
            return
            
        try:
            # Lấy post_id từ tiêu đề tin nhắn reply
            post_id_str = reply_to_text.split("ID:")[1].split(")")[0].strip()
            post_id = int(post_id_str)
        except Exception as e:
            logger.error(f"Không thể phân tích post_id từ tin nhắn reply: {str(e)}")
            bot.reply_to(message, "⚠️ Có lỗi xảy ra khi xác định ID bài viết cần sửa.")
            return
            
        post = database.get_post(post_id)
        if not post:
            bot.reply_to(message, "⚠️ Không tìm thấy bài viết này trong hệ thống.")
            return
            
        new_content = message.text.strip()
        if not new_content:
            bot.reply_to(message, "⚠️ Nội dung chỉnh sửa không thể để trống.")
            return
            
        # Cập nhật nội dung mới vào DB
        database.update_post(post_id, content=new_content)
        bot.reply_to(message, f"✅ Đã ghi nhận nội dung sửa đổi cho bài viết ID: {post_id}!")
        
        # Cập nhật lại tin nhắn xem trước ban đầu
        if post['tg_message_id']:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Duyệt đăng", callback_data=f"approve:{post_id}"),
                InlineKeyboardButton("✏️ Sửa nội dung", callback_data=f"edit_req:{post_id}")
            )
            markup.add(
                InlineKeyboardButton("❌ Hủy bỏ", callback_data=f"reject:{post_id}")
            )
            
            updated_caption = f"📝 **BÀI VIẾT ĐÃ CẬP NHẬT (ID: {post_id})**\n\n{new_content}"
            
            try:
                # Phải lấy Chat ID cấu hình
                chat_id = database.get_setting("tg_chat_id")
                if post['image_path'] and os.path.exists(post['image_path']):
                    bot.edit_message_caption(chat_id=chat_id, message_id=post['tg_message_id'], caption=updated_caption[:1024], reply_markup=markup, parse_mode="Markdown")
                else:
                    bot.edit_message_text(chat_id=chat_id, message_id=post['tg_message_id'], text=updated_caption, reply_markup=markup, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật tin nhắn duyệt gốc: {str(e)}")


def run_bot(token):
    """
    Hàm chạy vòng lặp Polling của Bot, được gọi trong Thread riêng.
    """
    global bot_instance
    logger.info("Bắt đầu khởi chạy Telegram Bot Polling Thread...")
    
    bot_instance = telebot.TeleBot(token)
    setup_bot_handlers(bot_instance)
    
    # Chạy vòng lặp polling thủ công để có thể kiểm soát tắt dừng an toàn
    while not stop_event.is_set():
        try:
            bot_instance.polling(non_stop=True, timeout=10, long_polling_timeout=5)
        except Exception as e:
            logger.error(f"Telegram Bot Polling Error: {str(e)}")
            time.sleep(5)  # Chờ 5s rồi thử lại
            
    logger.info("Telegram Bot Polling Thread đã dừng.")


def start_bot():
    """
    Bắt đầu chạy Bot trong một Thread chạy ngầm (nếu chưa chạy).
    """
    global polling_thread, bot_instance, stop_event
    
    token = database.get_setting("tg_bot_token")
    if not token:
        logger.warning("Telegram Bot Token chưa được cấu hình. Không thể chạy Bot.")
        return False
        
    if polling_thread and polling_thread.is_alive():
        logger.info("Telegram Bot đã đang hoạt động.")
        return True
        
    stop_event.clear()
    polling_thread = threading.Thread(target=run_bot, args=(token,), daemon=True)
    polling_thread.start()
    return True


def stop_bot():
    """
    Dừng Bot polling thread một cách an toàn.
    """
    global polling_thread, bot_instance, stop_event
    
    logger.info("Đang yêu cầu dừng Telegram Bot...")
    stop_event.set()
    
    if bot_instance:
        bot_instance.stop_polling()
        
    if polling_thread:
        polling_thread.join(timeout=3)
        polling_thread = None
        
    logger.info("Telegram Bot đã dừng hẳn.")
