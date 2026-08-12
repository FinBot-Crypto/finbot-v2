import json

# LONG Shadow
print('========== SHADOW LONG ==========')
d = json.load(open('/tmp/shadow_long.json'))
for tier_name, tier_data in d.get('tiers', {}).items():
    print('\nTier: {} ({} sims)'.format(tier_name, tier_data.get('total_simulations', 0)))
    
    # Trends
    rt = tier_data.get('ranking_trend', [])
    for item in rt:
        t = item.get('trend', '?')
        print('  Regime {}: avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
            t, item.get('avg_pnl', 0), item.get('count', 0), item.get('win_rate', 0)))
    
    # Best SL/TP
    sltp = tier_data.get('ranking_sltp', [])
    if sltp:
        print('  Best SL/TP configs:')
        for s in sltp[:3]:
            print('    {}: avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
                s.get('config', '?'), s.get('avg_pnl', 0), s.get('count', 0), s.get('win_rate', 0)))
    
    # Best RSI
    rsi = tier_data.get('ranking_rsi', [])
    if rsi:
        print('  RSI ranges:')
        for r in rsi:
            print('    {}: avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
                r.get('range', '?'), r.get('avg_pnl', 0), r.get('count', 0), r.get('win_rate', 0)))
    
    # Best combo
    bc = tier_data.get('best_combo')
    if bc:
        print('  Best combo: {} | avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
            bc.get('label', '?'), bc.get('avg_pnl', 0), bc.get('count', 0), bc.get('win_rate', 0)))

# SHORT Shadow
print('\n\n========== SHADOW SHORT ==========')
d = json.load(open('/tmp/shadow_short.json'))
for tier_name, tier_data in d.get('tiers', {}).items():
    print('\nTier: {} ({} sims)'.format(tier_name, tier_data.get('total_simulations', 0)))
    
    rt = tier_data.get('ranking_trend', [])
    for item in rt:
        t = item.get('trend', '?')
        print('  Regime {}: avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
            t, item.get('avg_pnl', 0), item.get('count', 0), item.get('win_rate', 0)))
    
    sltp = tier_data.get('ranking_sltp', [])
    if sltp:
        print('  Best SL/TP configs:')
        for s in sltp[:3]:
            print('    {}: avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
                s.get('config', '?'), s.get('avg_pnl', 0), s.get('count', 0), s.get('win_rate', 0)))
    
    rsi = tier_data.get('ranking_rsi', [])
    if rsi:
        print('  RSI ranges:')
        for r in rsi:
            print('    {}: avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
                r.get('range', '?'), r.get('avg_pnl', 0), r.get('count', 0), r.get('win_rate', 0)))
    
    bc = tier_data.get('best_combo')
    if bc:
        print('  Best combo: {} | avg_pnl={:+.3f}% | count={} | WR={:.1f}%'.format(
            bc.get('label', '?'), bc.get('avg_pnl', 0), bc.get('count', 0), bc.get('win_rate', 0)))
