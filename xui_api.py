import requests, json, uuid, time, base64, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MultiXUI:
    def __init__(self, server_cfg):
        self.cfg = server_cfg
        self.session = requests.Session()
        # အဆုံးမှာ / ပါခဲ့ရင် ဖြတ်ထားမယ်
        self.base_url = self.cfg['url'].rstrip('/')

    def login(self):
        try:
            res = self.session.post(f"{self.base_url}/login", 
                                    data={"username": self.cfg['user'], "password": self.cfg['pass']}, 
                                    verify=False, timeout=10)
            return res.status_code == 200
        except: return False

    def create_user(self, email, p_type, gb, days, inbound_id=None):
        if not self.login(): return None
        
        # main.py က ပို့လိုက်တဲ့ inbound_id ရှိရင် သုံးမယ်၊ မရှိရင် config က default ကို သုံးမယ်
        in_id = inbound_id if inbound_id else (self.cfg['vless_id'] if p_type == 'vless' else self.cfg['ss_id'])
        
        uid, sid = str(uuid.uuid4()), str(uuid.uuid4()).replace('-', '')[:16]
        expiry = int((time.time() + (days * 86400)) * 1000) if days > 0 else 0
        
        payload = {"id": in_id, "settings": json.dumps({"clients": [{"id": uid, "email": email, "totalGB": int(gb*1073741824), "expiryTime": expiry, "enable": True, "subId": sid}]})}
        
        try:
            # Add Client API
            add_res = self.session.post(f"{self.base_url}/panel/api/inbounds/addClient", data=payload, verify=False)
            if add_res.status_code != 200: return None
            
            # Get Inbound Info
            res_info = self.session.get(f"{self.base_url}/panel/api/inbounds/get/{in_id}", verify=False).json().get("obj")
            if not res_info: return None
            
            port = res_info.get("port")
            if p_type == 'vless':
                stream = json.loads(res_info.get("streamSettings"))
                path = stream.get("wsSettings", {}).get("path", "/").replace("/", "%2F")
                key = f"vless://{uid}@{self.cfg['domain']}:{port}?type={stream['network']}&security={stream['security']}&path={path}#N4-{email}"
            else:
                method = json.loads(res_info.get("settings")).get("method")
                auth = base64.b64encode(f"{method}:{uid}".encode()).decode()
                key = f"ss://{auth}@{self.cfg['domain']}:{port}#N4-Outline-{email}"
                
            return {"key": key, "sub": f"https://{self.cfg['domain']}:{self.cfg['sub_port']}/sub/{sid}"}
        except Exception as e:
            print(f"API Error: {e}")
            return None
