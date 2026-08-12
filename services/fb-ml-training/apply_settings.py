import urllib.request
import json

BASE = 'http://localhost:8000/api/settings'

changes = {
    # 1. Desabilitar SHORT Major (shadow mostra -0.172% PnL)
    "short_Major_allowed": False,
    
    # 2. Habilitar SHORT Strong Alt (shadow mostra +0.308%, WR 58.2%)
    "short_Strong Alt_allowed": True,
    "short_Strong Alt_min_rsi": 70,       # Shadow: 70-75 é o melhor range (+0.444%)
    "short_Strong Alt_sl": 5,             # Shadow: SL maiores performam melhor
    "short_Strong Alt_tp": 4,             # Shadow: TP=4 é o top
    
    # 3. Ajustar LONG Strong Alt SL/TP (atualmente SL=3/TP=3, muito apertado)
    # Mantendo desabilitado mas preparando caso reabilite
    # "long_Strong Alt_sl": 5,
    # "long_Strong Alt_tp": 5,
}

data = json.dumps(changes).encode('utf-8')
req = urllib.request.Request(BASE, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode())
    print('SUCCESS:', json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print('ERROR:', e.code, e.read().decode())
except Exception as e:
    print('ERROR:', str(e))

# Verify
req2 = urllib.request.Request(BASE)
resp2 = urllib.request.urlopen(req2)
settings = json.loads(resp2.read().decode())
print('\n=== SETTINGS VERIFICACAO ===')
for k in sorted(settings.keys()):
    if 'short' in k.lower() or 'long' in k.lower():
        print('{} = {}'.format(k, settings[k]))
