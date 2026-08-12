import json
d = json.load(open('/tmp/settings.json'))
for k, v in sorted(d.items()):
    print('{} = {}'.format(k, v))
