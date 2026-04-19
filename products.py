# products.py
VPN_PRODUCTS = {
    'n4_vip': {
        'name': "🚀 N4 VIP PRO (App)",
        'type': 'manual',
        'plans': [
            {'label': "💎 1 Month - 8,000 Ks", 'price': 8000, 'code': 'N4_1M'},
            {'label': "💎 1 Year - 75,000 Ks", 'price': 75000, 'code': 'N4_1Y'},
        ]
    },
    'v2ray_auto': {
        'name': "📡 V2Ray Auto Key",
        'type': 'auto',
        'server_key': 'S1',
        'p_type': 'vless',
        'plans': [
            {'label': "🔸 50GB (No Exp) - 5,000 Ks", 'price': 5000, 'gb': 50, 'days': 0},
            {'label': "🔸 100GB (1 Month) - 8,000 Ks", 'price': 8000, 'gb': 100, 'days': 30},
        ]
    },
    'outline_auto': {
        'name': "🔑 Outline Shadowsocks",
        'type': 'auto',
        'server_key': 'S1',
        'p_type': 'ss',
        'plans': [
            {'label': "🔸 100GB (No Exp) - 8,000 Ks", 'price': 8000, 'gb': 100, 'days': 0},
        ]
    }
}
