import requests
import paramiko
import psycopg2
import subprocess
import random

TARGET = "http://vulnerable-app:5000"

# ═══════════════════════════════════════════════════════
# Each payload returns:
#   {"id", "name", "type", "succeeded", "detail"}
# type = "malicious" | "legitimate" | "hygiene"
# ═══════════════════════════════════════════════════════


# ─────────── MALICIOUS ───────────

def m01_sqli_auth_bypass():
    r = requests.post(f"{TARGET}/login", data={
        "username": "' OR 1=1 --", "password": "x"
    }, allow_redirects=False)
    bypassed = r.status_code in (302, 200) and "session" in r.cookies
    return {"id": "M-01", "name": "SQLi Auth Bypass",
            "type": "malicious", "succeeded": bypassed,
            "detail": "Login bypassed" if bypassed else "Blocked"}


def m02_sqli_union():
    r = requests.get(f"{TARGET}/search", params={
        "q": "' UNION SELECT username,password FROM users --"
    })
    leaked = "password" in r.text.lower() or "testuser" in r.text
    return {"id": "M-02", "name": "SQLi UNION Extract",
            "type": "malicious", "succeeded": leaked,
            "detail": "Data extracted" if leaked else "Blocked"}


def m03_stored_xss():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    s.post(f"{TARGET}/profile/edit", data={
        "bio": '<script>fetch("http://judge:8080/xss")</script>'})
    r = s.get(f"{TARGET}/profile/1")
    hit = "<script>" in r.text
    return {"id": "M-03", "name": "Stored XSS",
            "type": "malicious", "succeeded": hit,
            "detail": "Script rendered" if hit else "Escaped"}


def m04_reflected_xss():
    r = requests.get(f"{TARGET}/search", params={
        "q": '<img src=x onerror=alert(1)>'})
    hit = "onerror" in r.text and "&lt;" not in r.text
    return {"id": "M-04", "name": "Reflected XSS",
            "type": "malicious", "succeeded": hit,
            "detail": "Reflected" if hit else "Escaped"}


def m05_idor():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    r = s.get(f"{TARGET}/profile/2")
    return {"id": "M-05", "name": "IDOR Profile",
            "type": "malicious", "succeeded": r.status_code == 200,
            "detail": "Data exposed" if r.status_code == 200 else "Denied"}


def m06_path_traversal():
    r = requests.get(f"{TARGET}/uploads/../../etc/passwd")
    hit = "root:" in r.text
    return {"id": "M-06", "name": "Path Traversal",
            "type": "malicious", "succeeded": hit,
            "detail": "/etc/passwd leaked" if hit else "Blocked"}


def m07_malicious_upload():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    s.post(f"{TARGET}/upload", files={
        "file": ("shell.py", b"import os; os.system('id')", "text/x-python")})
    r = s.get(f"{TARGET}/uploads/shell.py")
    return {"id": "M-07", "name": "Malicious Upload",
            "type": "malicious", "succeeded": r.status_code == 200,
            "detail": "Shell accessible" if r.status_code == 200 else "Rejected"}


def m08_ssh_root():
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect("vulnerable-app", port=22,
                  username="root", password="toor", timeout=5)
        c.close()
        return {"id": "M-08", "name": "SSH Root Login",
                "type": "malicious", "succeeded": True,
                "detail": "Root shell obtained"}
    except Exception:
        return {"id": "M-08", "name": "SSH Root Login",
                "type": "malicious", "succeeded": False,
                "detail": "Access denied"}


def m09_debug_leak():
    r = requests.get(f"{TARGET}/force-error-for-debug-check")
    hit = "Werkzeug" in r.text or "debugger" in r.text.lower()
    return {"id": "M-09", "name": "Debug Leak",
            "type": "malicious", "succeeded": hit,
            "detail": "Debugger exposed" if hit else "Hidden"}


def m10_db_default_creds():
    try:
        conn = psycopg2.connect(host="vulnerable-app", port=5432,
                                user="admin", password="password123",
                                dbname="appdb", connect_timeout=5)
        conn.close()
        return {"id": "M-10", "name": "DB Default Creds",
                "type": "malicious", "succeeded": True,
                "detail": "Connected with defaults"}
    except Exception:
        return {"id": "M-10", "name": "DB Default Creds",
                "type": "malicious", "succeeded": False,
                "detail": "Creds rotated"}


# ─────────── LEGITIMATE ───────────

def l01_normal_login():
    r = requests.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"
    }, allow_redirects=False)
    ok = r.status_code in (302, 200) and "session" in r.cookies
    return {"id": "L-01", "name": "Normal Login",
            "type": "legitimate", "succeeded": ok,
            "detail": "Login OK" if ok else "Broken"}


def l02_own_profile():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    r = s.get(f"{TARGET}/profile/1")
    return {"id": "L-02", "name": "Own Profile",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "Profile loaded" if r.status_code == 200 else "Broken"}


def l03_edit_bio():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    r = s.post(f"{TARGET}/profile/edit", data={
        "bio": "Security enthusiast, coffee lover."})
    return {"id": "L-03", "name": "Edit Bio (Clean)",
            "type": "legitimate", "succeeded": r.status_code in (200, 302),
            "detail": "Bio saved" if r.ok else "Failed"}


def l04_normal_search():
    r = requests.get(f"{TARGET}/search", params={"q": "python tutorial"})
    return {"id": "L-04", "name": "Normal Search",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "Search OK" if r.status_code == 200 else "Broken"}


def l05_valid_upload():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    jpeg = open("/judge/assets/legit_image.jpg", "rb").read()
    r = s.post(f"{TARGET}/upload", files={
        "file": ("photo.jpg", jpeg, "image/jpeg")})
    return {"id": "L-05", "name": "Valid Image Upload",
            "type": "legitimate", "succeeded": r.status_code in (200, 302),
            "detail": "Accepted" if r.ok else "Rejected"}


def l06_homepage():
    r = requests.get(f"{TARGET}/")
    return {"id": "L-06", "name": "Homepage",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "Loaded" if r.status_code == 200 else "Down"}


def l07_register():
    un = f"newuser_{random.randint(1000, 9999)}"
    r = requests.post(f"{TARGET}/register", data={
        "username": un, "email": f"{un}@test.com",
        "password": "SecureP@ss1"}, allow_redirects=False)
    return {"id": "L-07", "name": "Registration",
            "type": "legitimate", "succeeded": r.status_code in (200, 302),
            "detail": "Created" if r.status_code in (200, 302) else "Failed"}


def l08_password_change():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    r = s.post(f"{TARGET}/account/password", data={
        "current_password": "testpass",
        "new_password": "testpass"})
    return {"id": "L-08", "name": "Password Change",
            "type": "legitimate", "succeeded": r.status_code in (200, 302),
            "detail": "Updated" if r.ok else "Failed"}


def l09_health():
    r = requests.get(f"{TARGET}/api/health")
    return {"id": "L-09", "name": "Health Check",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "Healthy" if r.status_code == 200 else "Unhealthy"}


def l10_logout():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={
        "username": "testuser", "password": "testpass"})
    r = s.post(f"{TARGET}/logout", allow_redirects=False)
    return {"id": "L-10", "name": "Logout",
            "type": "legitimate", "succeeded": r.status_code in (200, 302),
            "detail": "Logged out" if r.status_code in (200, 302) else "Failed"}


def l11_about_page():
    r = requests.get(f"{TARGET}/about")
    return {"id": "L-11", "name": "About Page",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "Loaded" if r.status_code == 200 else "Down"}


def l12_api_status():
    r = requests.get(f"{TARGET}/api/status")
    return {"id": "L-12", "name": "API Status",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "OK" if r.status_code == 200 else "Down"}


def l13_alice_login():
    r = requests.post(f"{TARGET}/login", data={
        "username": "alice", "password": "alice123"
    }, allow_redirects=False)
    ok = r.status_code in (302, 200) and "session" in r.cookies
    return {"id": "L-13", "name": "Alice Login",
            "type": "legitimate", "succeeded": ok,
            "detail": "Login OK" if ok else "Broken"}


def l14_alice_own_profile():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={"username": "alice", "password": "alice123"})
    r = s.get(f"{TARGET}/profile/2")
    return {"id": "L-14", "name": "Alice Own Profile",
            "type": "legitimate", "succeeded": r.status_code == 200,
            "detail": "Profile loaded" if r.status_code == 200 else "Broken"}


def l15_alice_edit_bio():
    s = requests.Session()
    s.post(f"{TARGET}/login", data={"username": "alice", "password": "alice123"})
    r = s.post(f"{TARGET}/profile/edit", data={"bio": "I love cybersecurity!"})
    return {"id": "L-15", "name": "Alice Edit Bio",
            "type": "legitimate", "succeeded": r.status_code in (200, 302),
            "detail": "Bio saved" if r.ok else "Failed"}


# ─────────── HYGIENE (docker exec) ───────────

def _exec(cmd):
    r = subprocess.run(["docker", "exec", "vulnerable-app"] + cmd,
                       capture_output=True, text=True, timeout=10)
    return r.stdout


def h01_rogue_uid0():
    passwd = _exec(["cat", "/etc/passwd"])
    uid0 = [l.split(":")[0] for l in passwd.splitlines()
            if len(l.split(":")) > 2 and l.split(":")[2] == "0"]
    clean = uid0 == ["root"]
    return {"id": "H-01", "name": "Rogue UID-0",
            "type": "hygiene", "succeeded": clean,
            "detail": "Only root" if clean else f"UID-0 accounts: {uid0}"}


def h02_malicious_cron():
    cron = _exec(["cat", "/etc/cron.d/system-update"])
    clean = "curl" not in cron and "wget" not in cron
    return {"id": "H-02", "name": "Malicious Cron",
            "type": "hygiene", "succeeded": clean,
            "detail": "Clean" if clean else "Suspicious cron job found"}


def h03_entrypoint_backdoor():
    entry = _exec(["cat", "/app/entrypoint.sh"])
    patterns = ["/dev/tcp", "bash -i", "nc -e", "mkfifo"]
    clean = not any(p in entry for p in patterns)
    return {"id": "H-03", "name": "Entrypoint Backdoor",
            "type": "hygiene", "succeeded": clean,
            "detail": "Clean" if clean else "Backdoor pattern found"}


def h04_suid_find():
    perms = _exec(["stat", "-c", "%a", "/usr/bin/find"]).strip()
    clean = not perms.startswith("4")
    return {"id": "H-04", "name": "SUID find",
            "type": "hygiene", "succeeded": clean,
            "detail": "SUID removed" if clean else "SUID bit is set"}


def h05_attack_tools():
    nmap = _exec(["which", "nmap"]).strip()
    nc   = _exec(["which", "nc"]).strip()
    clean = not nmap and not nc
    return {"id": "H-05", "name": "Attack Tools",
            "type": "hygiene", "succeeded": clean,
            "detail": "Removed" if clean else "nmap/nc still installed"}


# ─────────── REGISTRY ───────────

ALL_PAYLOADS = [
    m01_sqli_auth_bypass, m02_sqli_union, m03_stored_xss, m04_reflected_xss,
    m05_idor, m06_path_traversal, m07_malicious_upload, m08_ssh_root,
    m09_debug_leak, m10_db_default_creds,
    l01_normal_login, l02_own_profile, l03_edit_bio, l04_normal_search,
    l05_valid_upload, l06_homepage, l07_register, l08_password_change,
    l09_health, l10_logout, l11_about_page, l12_api_status,
    l13_alice_login, l14_alice_own_profile, l15_alice_edit_bio,
]

HYGIENE_CHECKS = [
    h01_rogue_uid0, h02_malicious_cron, h03_entrypoint_backdoor,
    h04_suid_find, h05_attack_tools,
]
