import urllib.request
import json

BASE = 'http://localhost:8000/api/settings'

optimal_changes = {
    # Bloquear Tiers Tóxicos
    "long_Strong Alt_allowed": False,
    "short_Major_allowed": False,
    "short_High Volatility_allowed": False,
    
    # Ativar Tiers Lucrativos (comprovados pelo Shadow)
    "long_Major_allowed": True,
    "long_Major_min_score": 0.50,
    "long_Major_max_rsi": 30,
    "long_Major_sl": 4.0,
    "long_Major_tp": 4.0,
    "long_Major_allowed_regimes": ["bear", "neutral"],

    "long_High Volatility_allowed": True,
    "long_High Volatility_min_score": 0.55,
    "long_High Volatility_max_rsi": 25,
    "long_High Volatility_sl": 5.0,
    "long_High Volatility_tp": 5.0,
    "long_High Volatility_allowed_regimes": ["bear", "neutral"],

    "short_Strong Alt_allowed": True,
    "short_Strong Alt_min_score": 0.50,
    "short_Strong Alt_min_rsi": 70,
    "short_Strong Alt_sl": 5.0,
    "short_Strong Alt_tp": 4.0,
    "short_Strong Alt_allowed_regimes": ["bull", "neutral"],

    # Ajustes do Leme para amostragem sólida
    "leme_active": True,
    "leme_max_consecutive_sl": 3,
    "leme_min_win_rate": 50.0,
    "leme_cooldown_hours": 24,
    "leme_shadow_min_trades": 15,
    "leme_shadow_min_winrate": 65.0
}

data = json.dumps(optimal_changes).encode('utf-8')
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
print('\n=== SETTINGS ATUAIS (VERIFICADO) ===')
for k in sorted(settings.keys()):
    print('{} = {}'.format(k, settings[k]))
