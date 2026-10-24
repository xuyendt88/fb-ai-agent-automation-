import os
import datetime
from flask import Flask, request, jsonify
import gspread
from google import genai

app = Flask(__name__)

# 1. Khởi tạo Gemini Client (Sử dụng model gemini-2.5-flash tối ưu tốc độ và chi phí)
# Đảm bảo bạn đã cấu hình biến môi trường GEMINI_API_KEY trên môi trường chạy hoặc GitHub Secrets
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 2. Kết nối Google Sheets thông qua Service Account JSON
gc = gspread.service_account(filename='service_account.json')
# Mở file Google Sheets đã tạo
sh = gc.open("AI_Agent_Leads_Database")
# Chọn đúng tên tab trong Google Sheets của bạn
worksheet = sh.worksheet("Dữ liệu KH AI Agent")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Nhận dữ liệu từ Form đăng ký hoặc tin nhắn
        data = request.json
        name_company = data.get('name_company', 'Chưa rõ')
        pain_point = data.get('pain_point', 'Chưa rõ')

        # 3. Dùng Gemini phân tích nhu cầu và chấm điểm Lead (HOT / WARM / COLD)
        prompt = f"""
        Phân tích nhu cầu tự động hóa của khách hàng sau và đánh giá mức độ tiềm năng (HOT, WARM, COLD):
        Khách hàng/Công ty: {name_company}
        Nỗi đau/Nhu cầu: {pain_point}
        
        Chỉ trả về đúng định dạng: [MỨC ĐỘ] - [Lý do ngắn gọn trong 1 câu].
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        lead_score = response.text.strip()

        # 4. Ghi dữ liệu tự động vào Google Sheets
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([timestamp, name_company, pain_point, lead_score])

        return jsonify({
            "status": "success", 
            "message": "Đã lưu và chấm điểm lead thành công!",
            "lead_score": lead_score
        }), 200

    except Exception as e:
        # Bẫy lỗi ngầm để tránh sập server và dễ debug
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
