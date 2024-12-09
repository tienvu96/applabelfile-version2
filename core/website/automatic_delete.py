# import os
# import shutil
# import time
# from pathlib import Path

# # BASE_DIR là thư mục gốc của dự án, nơi chứa file manage.py
# BASE_DIR = Path(__file__).resolve().parent.parent

# # Đường dẫn tới thư mục media/gallery
# GALLERY_PATH = os.path.join(BASE_DIR, 'media', 'gallery')

# def clear_folder(folder_path):
#     """
#     Xóa tất cả các tệp và thư mục con trong thư mục được chỉ định.
#     """
#     if os.path.exists(folder_path):
#         for filename in os.listdir(folder_path):
#             file_path = os.path.join(folder_path, filename)
#             try:
#                 if os.path.isfile(file_path) or os.path.islink(file_path):
#                     os.remove(file_path)  # Xóa tệp
#                 elif os.path.isdir(file_path):
#                     shutil.rmtree(file_path)  # Xóa thư mục con
#             except Exception as e:
#                 print(f"Không thể xóa {file_path}. Lỗi: {e}")
#     else:
#         print(f"Thư mục {folder_path} không tồn tại.")

# def auto_clear_folder_every_5_minutes(folder_path):
#     """
#     Xóa tất cả các tệp trong thư mục cứ sau mỗi 5 phút.
#     """
#     while True:
#         clear_folder(folder_path)
#         print(f"Đã xóa tất cả các tệp trong thư mục: {folder_path}")
#         time.sleep(60 * 60 * 24)  # Đợi 5 phút (5 * 60 giây)

# # Bắt đầu quá trình tự động xóa tệp trong thư mục media/gallery
# auto_clear_folder_every_5_minutes(GALLERY_PATH)
