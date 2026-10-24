import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Lấy các biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "xuyendt88/fb-ai-agent-automation-") # Thay bằng tên repo GitHub của bạn nếu cần
FILE_PATH = "leads_log.json"

# Khởi tạo client Gemini mới nhất
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/", methods=["GET"])
def home():
    return "AI Agent Automation is running smoothly!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        name_company = data.get("name_company", "Không rõ")
        pain_point = data.get("pain_point", "Không rõ")

        # Tạo prompt cho Gemini chấm điểm lead
        prompt = f"""
        Bạn là một chuyên gia phân tích và đánh giá khách hàng tiềm năng (Lead Scoring Expert).
        Hãy phân tích thông tin công ty sau đây:
        - Tên công ty: {name_company}
        - Vấn đề/Nỗi đau (Pain point): {pain_point}

        Hãy trả về kết quả dưới dạng JSON thuần túy (không kèm markdown như ```json) với các trường sau:
        - score: Điểm số tiềm năng từ 1 đến 100 (kiểu số nguyên).
        - potential_level: Mức độ tiềm năng (Cao, Trung bình, Thấp).
        - analysis: Nhận xét ngắn gọn về nhu cầu và giải pháp gợi ý.
        """

        # Gọi Gemini API sử dụng model ổn định
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        
        gemini_text = response.text.strip()
        # Dọn dẹp markdown nếu Gemini trả về thừa ký tự
        if gemini_text.startswith("```json"):
            gemini_text = gemini_text[7:]
        if gemini_text.endswith("```"):
            gemini_text = gemini_text[:-3]
            
        ai_result = json.loads(gemini_text.strip())

        # Chuẩn bị dữ liệu lead hoàn chỉnh
        new_lead = {
            "name_company": name_company,
            "pain_point": pain_point,
            "ai_evaluation": ai_result
        }

        # Lưu lên GitHub
        success = save_lead_to_github(new_lead)
        if success:
            return jsonify({"status": "success", "data": new_lead}), 200
        else:
            return jsonify({"status": "error", "message": "Không thể commit lên GitHub."}), 500

    except Exception as e:
        # Trả về lỗi chi tiết dạng JSON để dễ debug
        return jsonify({"status": "error", "message": str(e)}), 500


def save_lead_to_github(new_lead):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    get_resp = requests.get(url, headers=headers)
    sha = None
    leads_list = []
    
    if get_resp.status_code == 200:
        file_data = get_resp.json()
        sha = file_data.get("sha")
        try:
            content_decoded = base64.b64decode(file_data["content"]).decode("utf-8")
            leads_list = json.loads(content_decoded)
            if not isinstance(leads_list, list):
                leads_list = []
        except:
            leads_list = []
            
    leads_list.append(new_lead)
    
    updated_content = json.dumps(leads_list, ensure_ascii=False, indent=4)
    encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": "Update leads_log.json automatically via AI Agent",
        "content": encoded_content,
        "branch": "main"
    }
    
    if sha:
        payload["sha"] = sha
        
    put_resp = requests.put(url, headers=headers, json=payload)
    return put_resp.status_code in [200, 201]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
