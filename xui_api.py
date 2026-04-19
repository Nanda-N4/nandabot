# xui_api.py
import requests, json, uuid, time, base64, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MultiXUI:
    def __init__(self, server_cfg):
        self.cfg = server_cfg
        self.session = requests.Session()

    def login(self):
        try:
            res = self.session.post(f"{self.cfg['url']}/login", 
                                    data={"username": self.cfg['user'], "password": self.cfg['pass']}, 
                                    verify=False, timeout=10)
            return res.status_code == 200
        except: return False

    def create_user(self, email, p_type, gb, days):
        if not self.login(): return None
        in_id = self.cfg['vless_id'] if p_type == 'vless' else self.cfg['ss_id']
        uid, sid = str(uuid.uuid4()), str(uuid.uuid4()).replace('-', '')[:16]
        expiry = int((time.time() + (days * 86400)) * 1000) if days > 0 else 0
        
        payload = {"id": in_id, "settings": json.dumps({"clients": [{"id": uid, "email": email, "totalGB": gb*1073741824, "expiryTime": expiry, "enable": True, "subId": sid}]})}
        try:
            self.session.post(f"{self.cfg['url']}/panel/api/inbounds/addClient", data=payload, verify=False)
            res = self.session.get(f"{self.cfg['url']}/panel/api/inbounds/get/{in_id}", verify=False).json().get("obj")
            port = res.get("port")
            if p_type == 'vless':
                stream = json.loads(res.get("streamSettings"))
                path = stream.get("wsSettings", {}).get("path", "/").replace("/", "%2F")
                key = f"vless://{uid}@{self.cfg['domain']}:{port}?type={stream['network']}&security={stream['security']}&path={path}#N4-{email}"
            else:
                method = json.loads(res.get("settings")).get("method")
                auth = base64.b64encode(f"{method}:{uid}".encode()).decode()
                key = f"ss://{auth}@{self.cfg['domain']}:{port}#N4-Outline-{email}"
            return {"key": key, "sub": f"https://{self.cfg['domain']}:{self.cfg['sub_port']}/sub/{sid}"}
        except: return None
