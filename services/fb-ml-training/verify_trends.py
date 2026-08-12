import json
d = json.load(open('/tmp/shadow_verify.json'))
for tier_name, tier_data in d.get('tiers', {}).items():
    rt = tier_data.get('ranking_trend', [])
    print('Tier: {} ({} trends)'.format(tier_name, len(rt)))
    for item in rt:
        print('  {}: avg_pnl={}, count={}, wr={}'.format(
            item.get('trend','?'), item.get('avg_pnl'), item.get('count'), item.get('win_rate')))
    print()

rt = d.get('ranking_trend', [])
print('Global ({} trends)'.format(len(rt)))
for item in rt:
    print('  {}: avg_pnl={}, count={}, wr={}'.format(
        item.get('trend','?'), item.get('avg_pnl'), item.get('count'), item.get('win_rate')))
