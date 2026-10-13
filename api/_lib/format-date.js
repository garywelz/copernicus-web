// Episode page date: "2026-08-21T02:38:37.986690" -> "August 21, 2026" (UTC calendar date).
// Lives under api/ because .vercelignore excludes lib/ (see api/_lib/further-reading.js).
const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/;
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function formatPubDate(raw) {
  const text = String(raw ?? '').trim();
  if (!text) return '';
  let date;
  const m = ISO.exec(text);
  if (m) {
    // A timestamp with no zone is taken as UTC (the backend writes UTC), never as the server's local time.
    const [, y, mo, d, h = '00', mi = '00', s = '00', zone = 'Z'] = m;
    date = new Date(`${y}-${mo}-${d}T${h}:${mi}:${s}${zone.length === 5 && !zone.includes(':') ? zone.slice(0, 3) + ':' + zone.slice(3) : zone}`);
  } else {
    date = new Date(text); // RSS style, e.g. "Thu, 21 Aug 2026 02:38:37 GMT"
  }
  if (Number.isNaN(date.getTime())) return text; // unknown format: show it as it was rather than hide it
  return `${MONTHS[date.getUTCMonth()]} ${date.getUTCDate()}, ${date.getUTCFullYear()}`;
}

module.exports = { formatPubDate };
