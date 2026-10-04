"""Run with python3 _checks/check_replay.py [built-site-directory]."""
import json
import math
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
assets = root / 'assets/realtime'
for name, count in [('min-01', 132), ('min-02', 132), ('max-01', 150), ('max-02', 151)]:
    trial = json.loads((assets / f'{name}.json').read_text())
    assert (assets / trial['video']).is_file()
    assert len(trial['timing']) == len(trial['metric']) == count
    assert len(trial['samples']) == len(trial['mapping'])
    for key in ['samples', 'mapping', 'timing', 'metric']:
        rows = trial[key]
        assert all(math.isfinite(x) for row in rows for x in row)
        assert all(b[0] > a[0] for a, b in zip(rows, rows[1:])), key
    for sample, mapping in zip(trial['samples'], trial['mapping']):
        assert len(sample) == 16 and sample[0] == mapping[1]
    assert trial['mapping'][0][1] == 0
    assert trial['mapping'][-1][1] == trial['duration']
if len(sys.argv) > 1:
    built = Path(sys.argv[1])
    html = (built / 'index.html').read_text()
    ids = re.findall(r'\bid="(replay-[^"]+)"', html)
    assert len(ids) == len(set(ids))
    for relative in re.findall(r'(?:src|href)="/gmrm/(assets/realtime/[^"]+)"', html):
        assert (built / relative).is_file(), relative
print('PASS: four trials, monotonic synchronization, finite samples and replay assets')
