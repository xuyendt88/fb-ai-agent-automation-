import os
import datetime
import base64
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# 1. Cấu hình Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 2. Cấu hình GitHub Repository đích để lưu dữ liệu Lead
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # Token cá nhân của bạn trên GitHub
GITHUB_REPO = "xuyendt88/fb-ai-agent-automation"  # Tên repo của bạn
FILE_PATH = "leads_log.json"                  # File lưu danh sách lead trên GitHub

def save_lead_to_github(new_lead):
    """Hàm tự động đọc, cập nhật và đẩy file leads_log.json lên GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Bước A: Lấy nội dung hiện tại của file trên GitHub (nếu có)
    response = requests.get(url, headers=headers)
    leads_list = []
    sha = None

    if response.status_code == 200:
        file_data = response.json()
        sha = file_data.get("sha")
        # Giải mã nội dung cũ từ Base64
        content_decoded = base64.b64decode(file_data["content"]).decode("utf-8")
        import json
        try:
            leads_list = json.loads(content_decoded)
        except:
            leads_list = []

    # Thêm lead mới vào danh sách
    leads_list.append(new_lead)

    # Bước B: Mã hóa lại danh sách mới sang chuẩn Base64
    import json
    updated_content = json.dumps(leads_list, ensure_ascii=False, indent=4)
    content_encoded = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

    # Bước C: Gửi yêu cầu Commit cập nhật file lên GitHub
    payload = {
        "message": f"Auto-save new lead: {new_lead['name_company']} at {new_lead['timestamp']}",
        "content": content_encoded,
        "sha": sha  # Bắt buộc phải có sha nếu file đã tồn tại để tránh xung đột
    }
    
    put_response = requests.put(url, headers=headers, json=payload)
    return put_response.status_code in [200, 201]

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        name_company = data.get('name_company', 'Chưa rõ')
        pain_point = data.get('pain_point', 'Chưa rõ')

        # 3. Dùng Gemini phân tích nhu cầu và chấm điểm Lead
        prompt = f"""
        Phân tích nhu cầu tự động hóa của khách hàng sau và đánh giá mức độ tiềm năng (HOT, WARM, COLD):
        Khách hàng/Công ty: {name_company}
        Nỗi đau/Nhu cầu: {pain_point}
        
        Chỉ trả về đúng định dạng: [MỨC ĐỘ] - [Lý do ngắn gọn trong 1 câu].
        """
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        lead_score = response.text.strip()

        # 4. Đóng gói dữ liệu và đẩy thẳng lên GitHub
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_lead = {
            "timestamp": timestamp,
            "name_company": name_company,
            "pain_point": pain_point,
            "lead_score": lead_score
        }

        success = save_lead_to_github(new_lead)

        if success:
            return jsonify({
                "status": "success", 
                "message": "Đã chấm điểm và lưu lead trực tiếp vào GitHub thành công!",
                "lead_score": lead_score
            }), 200
        else:
            return jsonify({"status": "error", "message": "Không thể commit lên GitHub."}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
