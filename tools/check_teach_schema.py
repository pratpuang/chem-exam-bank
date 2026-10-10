"""Does the live Supabase database have every column teach.html reads and writes?

Run before shipping any teach.html change (the git pre-push hook runs it). Exit 1 = the page expects a column the
database doesn't have: apply the SQL in supabase/schema.sql first, then push. Uses only the public key (RLS hides
all rows, but an unknown column still fails loudly), so it needs no secrets.
2026-10-11: a UI change shipped before its column (students.kind) and every save from every device was rejected."""
import json, re, sys, urllib.request, urllib.error
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
page = (ROOT / 'teach.html').read_text(encoding='utf-8')
cfg = (ROOT / 'supabase' / 'config.js').read_text(encoding='utf-8')
URL = re.search(r"url:\s*'([^']+)'", cfg).group(1); KEY = re.search(r"key:\s*'([^']+)'", cfg).group(1)
cols = {t: re.findall(r"'([a-z_]+)'", re.search(rf"const {v} = \[([^\]]+)\]", page).group(1)) for t, v in (('students', 'SCOL'), ('sessions', 'XCOL'))}
cols['app_state'] = ['owner', 'data']
bad = []
for table, cs in cols.items():
    for c in cs:
        req = urllib.request.Request(f'{URL}/rest/v1/{table}?select={c}&limit=0', headers={'apikey': KEY})
        try: urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as e:
            msg = json.loads(e.read() or b'{}').get('message', e.code); bad.append(f'{table}.{c}: {msg}')
        except Exception as e: print('could not reach Supabase:', e); sys.exit(2)
if bad:
    print('✗ teach.html expects columns the database does not have:'); [print('   ', b) for b in bad]
    print('  -> run the matching ALTER TABLE from supabase/schema.sql in the Supabase SQL editor, then push again.')
    sys.exit(1)
print(f'✓ schema OK · students {len(cols["students"])} · sessions {len(cols["sessions"])} columns all exist')
