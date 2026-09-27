import sys
import json
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

url_register = "https://kienhieu-marketing-api.onrender.com/api/v1/auth/register"
url_login = "https://kienhieu-marketing-api.onrender.com/api/v1/auth/login"

accounts = [
    # Gmail modern
    ("manager@gmail.com", "Manager@123", "Nguyễn Quản Lý (Manager)"),
    ("marketer@gmail.com", "Marketer@123", "Trần Chuyên Viên (Marketer)"),
    ("approver@gmail.com", "Approver@123", "Lê Phê Duyệt (Approver)"),
    # ICTU backward-compatible aliases so current live bundle works immediately
    ("manager@ictu.edu.vn", "Manager@123", "Nguyễn Quản Lý (Manager)"),
    ("marketer@ictu.edu.vn", "Marketer@123", "Trần Chuyên Viên (Marketer)"),
    ("approver@ictu.edu.vn", "Approver@123", "Lê Phê Duyệt (Approver)"),
]

for email, password, name in accounts:
    # Try register
    payload = json.dumps({
        "email": email,
        "password": password,
        "full_name": name,
        "role": "MARKETER"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url_register,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[REGISTER CREATED] {email}")
    except urllib.error.HTTPError as e:
        print(f"[REGISTER INFO] {email} -> {e.code}")

    # Now verify login
    login_payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    login_req = urllib.request.Request(
        url_login,
        data=login_payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(login_req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("access_token", "")[:12]
            print(f"[LOGIN VERIFIED OK] {email} -> Token {token}...")
    except urllib.error.HTTPError as e:
        print(f"[LOGIN FAILED] {email} -> HTTP {e.code} {e.read().decode()}")
