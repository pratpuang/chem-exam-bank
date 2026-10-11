// Live .ics feed of the teaching schedule for Apple/Google Calendar: /api/cal?t=<token>
// Reads through the teach_cal(token) database function with the public key (schema 005); no secrets live here.
const SB = 'https://qxotevxhlbjvfyidmeyi.supabase.co', KEY = 'sb_publishable_syQVgewlUUS8Kz8nrnAWyw_pJU13C3g';
const pad = n => String(n).padStart(2, '0');
// Bangkok is UTC+7 all year (no DST), so convert to UTC and skip VTIMEZONE
const utc = (date, time, addH = 0) => {
  const [y, m, d] = date.split('-').map(Number), [hh, mm] = time.split(':').map(Number);
  const t = new Date(Date.UTC(y, m - 1, d, hh - 7, mm) + addH * 3600e3);
  return `${t.getUTCFullYear()}${pad(t.getUTCMonth() + 1)}${pad(t.getUTCDate())}T${pad(t.getUTCHours())}${pad(t.getUTCMinutes())}00Z`;
};
const esc = s => String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
// lines over 75 octets must be folded (Thai = 3 bytes/char)
const fold = line => { const out = []; let cur = '', bytes = 0;
  for (const ch of line){ const b = Buffer.byteLength(ch); if (bytes + b > (out.length ? 74 : 75)){ out.push(cur); cur = ''; bytes = 0; } cur += ch; bytes += b; }
  out.push(cur); return out.join('\r\n '); };

module.exports = async (req, res) => {
  const tok = String(req.query.t || '');
  if (tok.length < 32){ res.status(404).send('not found'); return; }
  const r = await fetch(`${SB}/rest/v1/rpc/teach_cal`, { method: 'POST', headers: { apikey: KEY, Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json' }, body: JSON.stringify({ tok }) });
  if (!r.ok){ res.status(502).send('calendar source unavailable'); return; }
  const rows = await r.json();
  if (!rows.length){ res.status(404).send('not found'); return; }
  const stamp = utc(new Date().toISOString().slice(0, 10), '07:00');
  const L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//teach//chem-exam-bank//TH', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    'X-WR-CALNAME:สอนพิเศษ', 'X-WR-TIMEZONE:Asia/Bangkok', 'REFRESH-INTERVAL;VALUE=DURATION:PT15M', 'X-PUBLISHED-TTL:PT15M'];
  for (const x of rows){
    const done = x.status === 'done';
    L.push('BEGIN:VEVENT', `UID:${x.id}@teach.chem-exam-bank`, `DTSTAMP:${stamp}`,
      `DTSTART:${utc(x.date, x.time)}`, `DTEND:${utc(x.date, x.time, +x.h || 1)}`,
      `SUMMARY:${esc((done ? '✓ ' : '') + 'สอน' + x.name)}`);
    if (x.note) L.push(`DESCRIPTION:${esc(x.note)}`);
    if (x.updated_at) L.push(`LAST-MODIFIED:${x.updated_at.replace(/[-:]/g, '').replace(/\.\d+/, '').replace(/\+00(00)?$/, 'Z')}`);
    if (!done) L.push('BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + esc('สอน' + x.name), 'TRIGGER:-PT30M', 'END:VALARM');
    L.push('END:VEVENT');
  }
  L.push('END:VCALENDAR');
  res.setHeader('Content-Type', 'text/calendar; charset=utf-8');
  res.setHeader('Cache-Control', 'private, max-age=300');
  res.status(200).send(L.map(fold).join('\r\n') + '\r\n');
};
