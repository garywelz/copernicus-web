// Run with: node cloud-run-backend/tests/format_date.test.js
const assert = require('assert');
const { formatPubDate } = require('../../api/_lib/format-date');

assert.strictEqual(formatPubDate('2026-08-21T02:38:37.986690'), 'August 21, 2026');      // the raw text seen on the episode page
assert.strictEqual(formatPubDate('2026-08-21T02:38:37Z'), 'August 21, 2026');
assert.strictEqual(formatPubDate('2026-08-21T23:59:59.5+00:00'), 'August 21, 2026');
assert.strictEqual(formatPubDate('2026-08-21T23:30:00-05:00'), 'August 22, 2026');        // offsets are honoured, shown as the UTC date
assert.strictEqual(formatPubDate('2026-08-21T23:30:00-0500'), 'August 22, 2026');
assert.strictEqual(formatPubDate('2026-01-05'), 'January 5, 2026');                        // date only
assert.strictEqual(formatPubDate('Thu, 21 Aug 2026 02:38:37 GMT'), 'August 21, 2026');     // RSS style
assert.strictEqual(formatPubDate('2026-12-31T23:59:59'), 'December 31, 2026');             // no zone = UTC, whatever the server's own zone
assert.strictEqual(formatPubDate(''), '');
assert.strictEqual(formatPubDate(null), '');
assert.strictEqual(formatPubDate('sometime in August'), 'sometime in August');            // unknown format is shown, not hidden
console.log('format date: ok');
