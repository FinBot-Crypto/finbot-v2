import subprocess

containers = [
    'fb-web-dashboard',
    'fb-trade-decision',
    'fb-execution-futures',
    'fb-decision-engine',
    'fb-ml-validation',
    'fb-position-management',
    'fb-market-selection',
    'fb-execution',
    'fb-analytics',
    'fb-strategy-ml',
    'fb-ml-training'
]

for c in containers:
    print(f"{'='*60}")
    print(f"CONTAINER: {c}")
    print(f"{'='*60}")
    res = subprocess.run(['docker', 'logs', '--tail', '15', c], capture_output=True, text=True)
    out = res.stdout if res.stdout else res.stderr
    print(out.strip())
    print("\n")
