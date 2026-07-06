import os
from openai import OpenAI
from dotenv import load_dotenv

# Nạp các biến môi trường từ file .env
load_dotenv()

# Khởi tạo client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Lấy danh sách tất cả các file hiện có
response = client.files.list()

print(f"Tìm thấy tổng cộng {len(response.data)} file trên hệ thống.")

# Duyệt qua từng file và thực hiện xóa
for file in response.data:
    try:
        client.files.delete(file.id)
        print(f"Đã xoá thành công file | ID: {file.id} | Tên: {file.filename}")
    except Exception as e:
        print(f"Không thể xoá file {file.id}. Lỗi: {e}")

print("Quá trình xoá đã hoàn tất.")
