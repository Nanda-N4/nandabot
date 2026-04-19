import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
ADMIN_LINK = 'https://t.me/n4nd404'

SERVERS = {
    'S1': {
        'url': os.getenv('S1_URL'),
        'user': os.getenv('S1_USER'),
        'pass': os.getenv('S1_PASS'),
        'domain': os.getenv('S1_DOMAIN'),
        'sub_port': os.getenv('S1_SUB_PORT'),
        'vless_id': 1, 'ss_id': 2
    },
    'S2': {
        'url': os.getenv('S2_URL'),
        'user': os.getenv('S2_USER'),
        'pass': os.getenv('S2_PASS'),
        'domain': os.getenv('S2_DOMAIN'),
        'sub_port': os.getenv('S2_SUB_PORT'),
        'vless_id': 1, 'ss_id': 2
    }
}
