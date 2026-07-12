import streamlit as st
import os
import shutil
import database
import ai_generator
import fb_publisher
import telegram_bot

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Facebook AI Auto Poster",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thư mục lưu ảnh upload
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Tùy chỉnh CSS để giao diện trông hiện đại và chuyên nghiệp
st.markdown("""
    <style>
    /* Custom CSS */
    .main {
        background-color: #f8f9fa;
    }
    .stAppHeader {
        background-color: transparent;
    }
    .css-1dp5x8c {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    h1 {
        color: #1E3A8A;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        text-align: center;
        background: -webkit-linear-gradient(#1E3A8A, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .section-title {
        color: #1E3A8A;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        font-size: 1.25rem;
        font-weight: 600;
    }
    .badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 75%;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 0.25rem;
        color: #fff;
    }
    .badge-pending { background-color: #F59E0B; }
    .badge-approved { background-color: #10B981; }
    .badge-posted { background-color: #3B82F6; }
    .badge-rejected { background-color: #EF4444; }
    .badge-error { background-color: #7C3AED; }
    
    /* Giao diện nút bấm */
    .stButton>button {
        border-radius: 8px;
        background: linear-gradient(135deg, #3B82F6, #1D4ED8);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# Khởi động Telegram Bot ở background nếu đã cấu hình Token
if database.get_setting("tg_bot_token"):
    try:
        telegram_bot.start_bot()
    except Exception as e:
        st.sidebar.error(f"Không thể khởi động Telegram Bot: {str(e)}")

# Sidebar điều hướng và hiển thị trạng thái
with st.sidebar:
    st.image("https://img.icons8.com/color/144/facebook-new.png", width=70)
    st.markdown("## **Facebook AI Poster**")
    st.markdown("---")
    
    # Kiểm tra trạng thái Bot
    bot_token = database.get_setting("tg_bot_token")
    if bot_token:
        bot_running = telegram_bot.polling_thread and telegram_bot.polling_thread.is_alive()
        if bot_running:
            st.success("🟢 Telegram Bot: Đang hoạt động")
        else:
            st.warning("🟡 Telegram Bot: Chưa hoạt động")
            if st.button("🚀 Khởi chạy Bot"):
                if telegram_bot.start_bot():
                    st.rerun()
    else:
        st.info("🔴 Telegram Bot: Chưa cấu hình Token")
        
    st.markdown("---")
    st.markdown("💡 **Cách hoạt động:**\n1. Nhập cấu hình API ở tab **Cài đặt**.\n2. Tải ảnh lên và bấm **Tạo bài viết với AI**.\n3. Xem thử nội dung, chỉnh sửa nếu cần và bấm **Gửi duyệt sang Telegram**.\n4. Mở Telegram kiểm tra tin nhắn của Bot, bấm **Duyệt đăng** (hoặc reply để chỉnh sửa).")

# Tiêu đề chính
st.markdown("<h1>🤖 Facebook AI Auto Poster 📝</h1>", unsafe_allow_html=True)

# Khởi tạo Tabs
tab_create, tab_history, tab_settings = st.tabs([
    "✍️ Tạo Bài Đăng Mới", 
    "📜 Lịch Sử & Hàng Đợi", 
    "⚙️ Cài Đặt Hệ Thống"
])

# ----------------- TAB: TẠO BÀI ĐĂNG MỚI -----------------
with tab_create:
    st.markdown("<div class='section-title'>Cấu hình Nội dung Bài đăng</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        subject = st.text_input("Chủ đề bài đăng:", value="Phong trào thi đua 3 nhất")
        unit = st.text_input("Đơn vị thực hiện:", value="Phân trại số 1, trại giam Phú Hòa")
        extra_req = st.text_area("Yêu cầu thêm đối với AI (Ví dụ: Ngắn gọn, có hashtag, vui vẻ...):", 
                                 value="nội dung ngắn gọn, súc tích, chia bố cục rõ ràng, có emoji")
        
    with col2:
        uploaded_file = st.file_uploader("Hình ảnh đăng kèm (Bắt buộc):", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Ảnh xem trước", use_container_width=True)

    st.markdown("---")
    
    # Session state để lưu bài đăng nháp vừa tạo
    if 'draft_content' not in st.session_state:
        st.session_state.draft_content = ""
        
    # Nút bấm tạo nháp với AI
    if st.button("🪄 Tạo bài viết bằng AI (Gemini)"):
        gemini_api_key = database.get_setting("gemini_api_key")
        if not gemini_api_key:
            st.error("⚠️ Vui lòng cấu hình Gemini API Key tại tab 'Cài đặt' trước!")
        else:
            with st.spinner("Gemini đang suy nghĩ và viết bài..."):
                try:
                    draft = ai_generator.generate_fb_post(
                        api_key=gemini_api_key,
                        subject=subject,
                        unit=unit,
                        extra_requirements=extra_req
                    )
                    st.session_state.draft_content = draft
                    st.success("Tạo nội dung bài viết thành công!")
                except Exception as e:
                    st.error(f"Lỗi: {str(e)}")

    # Giao diện xem trước và cho phép chỉnh sửa nhanh trước khi gửi
    if st.session_state.draft_content:
        st.markdown("<div class='section-title'>Xem trước nội dung (Bạn có thể chỉnh sửa tại đây)</div>", unsafe_allow_html=True)
        
        edited_content = st.text_area("Nội dung bài viết:", value=st.session_state.draft_content, height=200)
        
        if st.button("✈️ Gửi sang Telegram để Duyệt đăng"):
            if not uploaded_file:
                st.error("⚠️ Bạn phải chọn 1 hình ảnh để đăng kèm theo yêu cầu bố cục (Nội dung + hình ảnh)!")
            else:
                # Kiểm tra cấu hình Telegram
                tg_bot_token = database.get_setting("tg_bot_token")
                tg_chat_id = database.get_setting("tg_chat_id")
                
                if not tg_bot_token or not tg_chat_id:
                    st.error("⚠️ Vui lòng cấu hình Telegram Bot Token và Chat ID trong phần 'Cài đặt' trước!")
                else:
                    with st.spinner("Đang lưu trữ hình ảnh và gửi sang Telegram duyệt..."):
                        try:
                            # Đảm bảo Bot đã khởi động
                            telegram_bot.start_bot()
                            
                            # Lưu file ảnh cục bộ
                            file_ext = os.path.splitext(uploaded_file.name)[1]
                            local_filename = f"photo_{int(os.path.getmtime(UPLOAD_DIR)) if os.path.exists(UPLOAD_DIR) else 1}{file_ext}"
                            local_image_path = os.path.join(UPLOAD_DIR, local_filename)
                            
                            with open(local_image_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                                
                            # Lưu vào database
                            post_id = database.create_post(
                                content=edited_content,
                                image_path=local_image_path,
                                status='pending'
                            )
                            
                            # Gửi sang telegram
                            telegram_bot.send_post_to_telegram(post_id)
                            
                            st.success(f"🎉 Đã gửi bài viết ID {post_id} thành công sang Telegram. Hãy mở Telegram của bạn để duyệt đăng!")
                            # Reset draft
                            st.session_state.draft_content = ""
                            
                        except Exception as e:
                            st.error(f"Gửi duyệt thất bại: {str(e)}")

# ----------------- TAB: LỊCH SỬ & HÀNG ĐỢI -----------------
with tab_history:
    st.markdown("<div class='section-title'>Danh sách bài viết gần đây</div>", unsafe_allow_html=True)
    
    posts = database.get_posts()
    if not posts:
        st.info("Chưa có bài viết nào được tạo. Hãy sang Tab 'Tạo bài đăng' để bắt đầu!")
    else:
        for p in posts:
            with st.container():
                # Tạo header cho mỗi bài viết
                col_id, col_status, col_date = st.columns([1, 2, 4])
                col_id.markdown(f"**ID: {p['id']}**")
                
                # Hiển thị badge trạng thái
                status_mapping = {
                    'pending': ('🕒 Chờ duyệt', 'badge-pending'),
                    'approved': ('✅ Đã duyệt', 'badge-approved'),
                    'posted': ('🚀 Đã đăng', 'badge-posted'),
                    'rejected': ('❌ Đã hủy', 'badge-rejected'),
                    'error': ('⚠️ Lỗi', 'badge-error')
                }
                status_text, status_class = status_mapping.get(p['status'], ('Không rõ', ''))
                col_status.markdown(f"<span class='badge {status_class}'>{status_text}</span>", unsafe_allow_html=True)
                col_date.write(f"Tạo lúc: {p['created_at']}")
                
                # Chi tiết bài viết
                col_img, col_text = st.columns([1, 3])
                
                with col_img:
                    if p['image_path'] and os.path.exists(p['image_path']):
                        st.image(p['image_path'], use_container_width=True)
                    else:
                        st.write("Không có hình ảnh")
                        
                with col_text:
                    st.code(p['content'], language="text")
                    if p['status'] == 'posted' and p['fb_post_id']:
                        st.markdown(f"🔗 **Link đăng**: [Xem trên Facebook](https://facebook.com/{p['fb_post_id']})")
                    elif p['status'] == 'error' and p['error_message']:
                        st.error(f"Chi tiết lỗi: {p['error_message']}")
                        
                st.markdown("---")

# ----------------- TAB: CÀI ĐẶT HỆ THỐNG -----------------
with tab_settings:
    st.markdown("<div class='section-title'>Cấu hình API Keys và Tài khoản</div>", unsafe_allow_html=True)
    
    # Đọc cấu hình hiện tại từ database
    curr_gemini_key = database.get_setting("gemini_api_key")
    curr_tg_bot_token = database.get_setting("tg_bot_token")
    curr_tg_chat_id = database.get_setting("tg_chat_id")
    curr_fb_page_id = database.get_setting("fb_page_id", "61590891416912")
    curr_fb_page_token = database.get_setting("fb_page_token")
    
    with st.form("settings_form"):
        gemini_api_key = st.text_input("1. Gemini API Key:", value=curr_gemini_key, type="password", 
                                      help="Dùng để sinh bài viết. Lấy tại Google AI Studio.")
        
        st.markdown("---")
        tg_bot_token = st.text_input("2. Telegram Bot Token:", value=curr_tg_bot_token, type="password",
                                     help="Bot Token lấy từ @BotFather khi tạo bot mới.")
        tg_chat_id = st.text_input("3. Telegram Chat ID (của bạn):", value=curr_tg_chat_id,
                                   help="Dùng để Bot gửi tin duyệt bài cho bạn. Nhắn tin với @userinfobot để lấy ID cá nhân.")
        
        st.markdown("---")
        fb_page_id = st.text_input("4. Facebook Page ID:", value=curr_fb_page_id,
                                   help="ID Fanpage của bạn. Ví dụ của trang bạn cung cấp là: 61590891416912")
        fb_page_token = st.text_input("5. Facebook Page Access Token (Vĩnh viễn):", value=curr_fb_page_token, type="password",
                                      help="Token có quyền pages_manage_posts để đăng bài. Lấy từ Facebook Developer App.")
        
        submitted = st.form_submit_button("💾 Lưu cấu hình")
        
        if submitted:
            database.set_setting("gemini_api_key", gemini_api_key)
            database.set_setting("tg_bot_token", tg_bot_token)
            database.set_setting("tg_chat_id", tg_chat_id)
            database.set_setting("fb_page_id", fb_page_id)
            database.set_setting("fb_page_token", fb_page_token)
            
            st.success("🎉 Đã lưu cấu hình thành công!")
            
            # Khởi động / Khởi động lại Telegram Bot
            if tg_bot_token:
                with st.spinner("Đang khởi động Telegram Bot..."):
                    try:
                        telegram_bot.stop_bot()
                        telegram_bot.start_bot()
                        st.success("Telegram Bot khởi động thành công!")
                    except Exception as e:
                        st.error(f"Khởi động Bot lỗi: {str(e)}")
            st.rerun()

    # Hướng dẫn chi tiết cách lấy Facebook Access Token vĩnh viễn
    with st.expander("ℹ️ Hướng dẫn cách lấy Page Access Token vĩnh viễn (Long-lived Token)"):
        st.markdown("""
        **Bước 1: Tạo App Developer**
        1. Truy cập [developers.facebook.com](https://developers.facebook.com) và đăng nhập.
        2. Nhấp **My Apps** -> **Create App** (Chọn loại app là **Other** -> **Business**).
        
        **Bước 2: Sử dụng công cụ Graph API Explorer**
        1. Truy cập [Tools > Graph API Explorer](https://developers.facebook.com/tools/explorer/).
        2. Ở cột bên phải:
           - Mục **Meta App**: Chọn app bạn vừa tạo.
           - Mục **User or Page**: Chọn **Get Page Access Token** và chọn Trang của bạn.
           - Mục **Permissions**: Thêm các quyền `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.
        3. Nhấp nút **Generate Access Token** màu xanh và đăng nhập cấp quyền cho Page.
        4. Copy token ngắn hạn hiển thị ở ô *Access Token*.
        
        **Bước 3: Đổi Token ngắn hạn thành Token vĩnh viễn**
        1. Truy cập công cụ [Access Token Tool](https://developers.facebook.com/tools/accesstoken/).
        2. Tìm mục ứng dụng của bạn, nhấp **Debug** bên cạnh Page Token.
        3. Cuộn xuống và nhấp nút **Extend Access Token** để tạo token có thời hạn 60 ngày.
        4. Để lấy token vĩnh viễn (không bao giờ hết hạn), bạn gọi GET request sau trong trình duyệt:
           `https://graph.facebook.com/v20.0/me/accounts?access_token={TOKEN_60_NGAY_VUA_LAY}`
        5. Kết quả JSON trả về sẽ chứa trường `access_token` của Page của bạn. Đó là token vĩnh viễn. Hãy copy và điền vào ô cấu hình ở trên.
        """)
