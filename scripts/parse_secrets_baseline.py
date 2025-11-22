import json
from pathlib import Path
p = Path('.secrets.baseline')
out = Path('.secrets.report.txt')
if not p.exists():
    print('No baseline found')
    raise SystemExit(1)
obj = json.loads(p.read_text(encoding='utf-8', errors='ignore'))
results = obj.get('results', {})
report_lines = []
report_lines.append('Detect-secrets baseline report')
report_lines.append('==============================')
report_lines.append('')
count = 0
for fn, arr in results.items():
    # normalize
    if fn.startswith('.venv') or fn.startswith('./.venv') or fn.startswith('venv'):
        continue
    for item in arr:
        count += 1
        report_lines.append(f'{count}. File: {fn}\n   Type: {item.get("type")}\n   Line: {item.get("line_number")}')

if count == 0:
    report_lines.append('No findings outside .venv')

out.write_text('\n'.join(report_lines))
print(out)
