import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from google import genai
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Lấy các biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "xuyendt88/fb-ai-agent-automation-") 
FILE_PATH = "leads_log.json"
POSTS_FILE_PATH = "group_posts_log.json"

# Khởi tạo client Gemini mới nhất
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/", methods=["GET"])
def home():
    return "AI Agent Automation & Content Engine is running smoothly!", 200

# ==========================================
# 1. TÍNH NĂNG CŨ: XỬ LÝ VÀ CHẤM ĐIỂM LEAD
# ==========================================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        name_company = data.get("name_company", "Không rõ")
        pain_point = data.get("pain_point", "Không rõ")

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

        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        
        gemini_text = response.text.strip()
        if gemini_text.startswith("```json"):
            gemini_text = gemini_text[7:]
        if gemini_text.endswith("```"):
            gemini_text = gemini_text[:-3]
            
        ai_result = json.loads(gemini_text.strip())

        new_lead = {
            "name_company": name_company,
            "pain_point": pain_point,
            "ai_evaluation": ai_result
        }

        success = save_lead_to_github(new_lead)
        if success:
            return jsonify({"status": "success", "data": new_lead}), 200
        else:
            return jsonify({"status": "error", "message": "Không thể commit lên GitHub."}), 500

    except Exception as e:
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


# ==========================================
# 2. TÍNH NĂNG MỚI: TỰ ĐỘNG TẠO NỘI DUNG NUÔI NHÓM
# ==========================================
post_counter = 0

def generate_automated_content():
    global post_counter
    post_counter += 1
    
    # Xoay vòng giữa 2 chủ đề: Tự động hóa doanh nghiệp & Marketing bằng AI
    if post_counter % 2 != 0:
        topic = "Tự động hóa doanh nghiệp (Tối ưu quy trình vận hành, tiết kiệm nhân sự, dùng bot/phần mềm thay thế công việc thủ công)"
    else:
        topic = "Marketing bằng AI (Cách dùng AI viết content, tối ưu quảng cáo, sáng tạo chiến dịch, nuôi kênh tự động)"

    prompt = f"""
    Bạn là một chuyên gia hàng đầu về {topic}. 
    Hãy viết một bài đăng Facebook cực kỳ thu hút, ngắn gọn, súc tích, mang tính thực chiến cao để đăng lên cộng đồng kinh doanh.
    Yêu cầu bắt buộc:
    1. Tiêu đề (Headline) giật tít mạnh mẽ, chạm đúng "nỗi đau" của chủ doanh nghiệp hoặc marketer.
    2. Nội dung chia sẻ 3 bước hoặc 3 mẹo thực tế có thể áp dụng ngay.
    3. Cuối bài phải có một phần "Tài liệu tặng kèm độc quyền" cực giá trị liên quan đến chủ đề để kích thích mọi người bình luận/tham gia nhóm.
    4. Kèm theo 3-4 hashtag phù hợp.
    Trả về định dạng JSON thuần túy (không kèm markdown) gồm các trường: "title", "content", "gift_material", "topic".
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        ai_text = response.text.strip()
        if ai_text.startswith("```json"):
            ai_text = ai_text[7:]
        if ai_text.endswith("```"):
            ai_text = ai_text[:-3]
            
        post_data = json.loads(ai_text.strip())
        save_post_to_github(post_data, topic)
    except Exception as e:
        print(f"Lỗi khi AI tự động tạo bài viết: {e}")

def save_post_to_github(post_content, topic):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    existing_posts = []
    sha = None
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        file_data = resp.json()
        sha = file_data.get("sha")
        try:
            content_decoded = base64.b64decode(file_data["content"]).decode("utf-8")
            existing_posts = json.loads(content_decoded)
            if not isinstance(existing_posts, list):
                existing_posts = []
        except:
            existing_posts = []

    new_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "data": post_content
    }
    existing_posts.insert(0, new_entry)

    updated_content = json.dumps(existing_posts, ensure_ascii=False, indent=4)
    encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"AI Agent auto-generated post about {topic}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
        
    requests.put(url, headers=headers, json=payload)

# Lịch chạy tự động: 3 bài/ngày (8h00, 13h00, 20h00)
scheduler = BackgroundScheduler()
scheduler.add_job(func=generate_automated_content, trigger="cron", hour="8,13,20", minute=0)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
