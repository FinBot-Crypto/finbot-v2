import json

d = json.load(open('/tmp/ops_analysis.json'))
closed = d.get('closed', [])
print('Total closed orders:', len(closed))
print('Total PnL (API):', d.get('total_pnl'))
print()

by_day = {}
by_direction = {'LONG': {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0},
                'SHORT': {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0}}
by_tier = {}
by_exit = {}
by_symbol = {}
by_leverage = {}
all_losses = []

for o in closed:
    ts = o.get('created_at', '')[:5]  # "27/07"
    pnl_pct = float(o.get('pnl_pct', 0) or 0)
    direction = o.get('direction', 'LONG')
    tier = o.get('tier', 'Unknown')
    symbol = o.get('symbol', '?')
    exit_reason = o.get('exit_reason', '?')
    leverage = o.get('leverage', 1)
    score = o.get('score', 0)
    rsi = o.get('rsi', 0)
    is_futures = o.get('is_futures', False)
    
    # By day
    if ts not in by_day:
        by_day[ts] = {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0}
    by_day[ts]['pnl'] += pnl_pct
    by_day[ts]['count'] += 1
    if pnl_pct > 0:
        by_day[ts]['wins'] += 1
    else:
        by_day[ts]['losses'] += 1
    
    # By direction
    if direction in by_direction:
        by_direction[direction]['pnl'] += pnl_pct
        by_direction[direction]['count'] += 1
        if pnl_pct > 0:
            by_direction[direction]['wins'] += 1
        else:
            by_direction[direction]['losses'] += 1
    
    # By tier
    if tier not in by_tier:
        by_tier[tier] = {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0}
    by_tier[tier]['pnl'] += pnl_pct
    by_tier[tier]['count'] += 1
    if pnl_pct > 0:
        by_tier[tier]['wins'] += 1
    else:
        by_tier[tier]['losses'] += 1
    
    # By exit reason
    if exit_reason not in by_exit:
        by_exit[exit_reason] = {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0}
    by_exit[exit_reason]['pnl'] += pnl_pct
    by_exit[exit_reason]['count'] += 1
    if pnl_pct > 0:
        by_exit[exit_reason]['wins'] += 1
    else:
        by_exit[exit_reason]['losses'] += 1
    
    # By symbol
    if symbol not in by_symbol:
        by_symbol[symbol] = {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0}
    by_symbol[symbol]['pnl'] += pnl_pct
    by_symbol[symbol]['count'] += 1
    if pnl_pct > 0:
        by_symbol[symbol]['wins'] += 1
    else:
        by_symbol[symbol]['losses'] += 1
    
    # By leverage
    lev_key = '{}x{}'.format(leverage, ' (Futures)' if is_futures else ' (Spot)')
    if lev_key not in by_leverage:
        by_leverage[lev_key] = {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0}
    by_leverage[lev_key]['pnl'] += pnl_pct
    by_leverage[lev_key]['count'] += 1
    if pnl_pct > 0:
        by_leverage[lev_key]['wins'] += 1
    else:
        by_leverage[lev_key]['losses'] += 1
    
    all_losses.append(o)

def wr(wins, count):
    return round(wins / count * 100, 1) if count > 0 else 0

print('=== POR DIA ===')
for day in sorted(by_day.keys(), reverse=True):
    d2 = by_day[day]
    print('{}: PnL%={:+.2f}% | {} trades | {} W / {} L | WR {:.1f}%'.format(
        day, d2['pnl'], d2['count'], d2['wins'], d2['losses'], wr(d2['wins'], d2['count'])))

print()
print('=== POR DIRECAO ===')
for d_name in ['LONG', 'SHORT']:
    d2 = by_direction[d_name]
    print('{}: PnL%={:+.2f}% | {} trades | {} W / {} L | WR {:.1f}%'.format(
        d_name, d2['pnl'], d2['count'], d2['wins'], d2['losses'], wr(d2['wins'], d2['count'])))

print()
print('=== POR TIER ===')
for t in sorted(by_tier.keys()):
    d2 = by_tier[t]
    print('{}: PnL%={:+.2f}% | {} trades | {} W / {} L | WR {:.1f}%'.format(
        t, d2['pnl'], d2['count'], d2['wins'], d2['losses'], wr(d2['wins'], d2['count'])))

print()
print('=== POR EXIT REASON ===')
for r in sorted(by_exit.keys()):
    d2 = by_exit[r]
    print('{}: PnL%={:+.2f}% | {} trades'.format(r, d2['pnl'], d2['count']))

print()
print('=== POR ALAVANCAGEM ===')
for lev in sorted(by_leverage.keys()):
    d2 = by_leverage[lev]
    print('{}: PnL%={:+.2f}% | {} trades | WR {:.1f}%'.format(
        lev, d2['pnl'], d2['count'], wr(d2['wins'], d2['count'])))

print()
print('=== TOP 10 PIORES TRADES ===')
worst = sorted(all_losses, key=lambda x: float(x.get('pnl_pct', 0) or 0))[:10]
for o in worst:
    pnl_pct = float(o.get('pnl_pct', 0) or 0)
    print('{} {} {} | PnL={:+.2f}% | score={} | rsi={} | lev={} | exit={} | tier={}'.format(
        o.get('created_at', ''), o.get('direction', '?'), o.get('symbol', '?'),
        pnl_pct, o.get('score', '?'), o.get('rsi', '?'),
        o.get('leverage', '?'), o.get('exit_reason', '?'), o.get('tier', '?')))

print()
print('=== TOP 10 MELHORES TRADES ===')
best = sorted(all_losses, key=lambda x: float(x.get('pnl_pct', 0) or 0), reverse=True)[:10]
for o in best:
    pnl_pct = float(o.get('pnl_pct', 0) or 0)
    print('{} {} {} | PnL={:+.2f}% | score={} | rsi={} | lev={} | exit={} | tier={}'.format(
        o.get('created_at', ''), o.get('direction', '?'), o.get('symbol', '?'),
        pnl_pct, o.get('score', '?'), o.get('rsi', '?'),
        o.get('leverage', '?'), o.get('exit_reason', '?'), o.get('tier', '?')))

# Score distribution analysis
print()
print('=== DISTRIBUICAO DE SCORE ===')
score_ranges = {'<0.50': {'w': 0, 'l': 0, 'pnl': 0}, '0.50-0.55': {'w': 0, 'l': 0, 'pnl': 0},
                '0.55-0.60': {'w': 0, 'l': 0, 'pnl': 0}, '0.60-0.65': {'w': 0, 'l': 0, 'pnl': 0},
                '0.65-0.70': {'w': 0, 'l': 0, 'pnl': 0}, '>=0.70': {'w': 0, 'l': 0, 'pnl': 0}}
for o in closed:
    s = float(o.get('score', 0) or 0)
    p = float(o.get('pnl_pct', 0) or 0)
    if s < 0.50: k = '<0.50'
    elif s < 0.55: k = '0.50-0.55'
    elif s < 0.60: k = '0.55-0.60'
    elif s < 0.65: k = '0.60-0.65'
    elif s < 0.70: k = '0.65-0.70'
    else: k = '>=0.70'
    score_ranges[k]['pnl'] += p
    if p > 0: score_ranges[k]['w'] += 1
    else: score_ranges[k]['l'] += 1

for k, v in score_ranges.items():
    total = v['w'] + v['l']
    if total > 0:
        print('{}: {} trades | {} W / {} L | WR {:.1f}% | PnL%={:+.2f}%'.format(
            k, total, v['w'], v['l'], wr(v['w'], total), v['pnl']))

# RSI distribution analysis
print()
print('=== DISTRIBUICAO DE RSI (LONG entradas) ===')
for o in closed:
    if o.get('direction') == 'LONG':
        r = float(o.get('rsi', 0) or 0)
        p = float(o.get('pnl_pct', 0) or 0)
        result = 'WIN' if p > 0 else 'LOSS'
        print('  RSI={:.1f} | {} | PnL={:+.2f}% | {}'.format(r, o.get('symbol', '?'), p, result))

print()
print('=== DISTRIBUICAO DE RSI (SHORT entradas) ===')
for o in closed:
    if o.get('direction') == 'SHORT':
        r = float(o.get('rsi', 0) or 0)
        p = float(o.get('pnl_pct', 0) or 0)
        result = 'WIN' if p > 0 else 'LOSS'
        print('  RSI={:.1f} | {} | PnL={:+.2f}% | {}'.format(r, o.get('symbol', '?'), p, result))
