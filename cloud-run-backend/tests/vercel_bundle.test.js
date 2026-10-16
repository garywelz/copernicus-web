// Run with: node cloud-run-backend/tests/vercel_bundle.test.js
// Every local file an api/ function requires must survive .vercelignore. The first Further reading change put its helper in lib/,
// which .vercelignore excludes, so every episode page returned FUNCTION_INVOCATION_FAILED in production while all unit tests passed.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', '..');
const patterns = fs.readFileSync(path.join(root, '.vercelignore'), 'utf8').split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith('#') && !l.startsWith('!'));

function globToRegex(g) {
  return new RegExp('^' + g.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*') + '$');
}
// A small model of .gitignore-style matching, enough for the patterns this repo uses (dir/, *.ext, name*.ext, plain names).
function ignored(rel) {
  const parts = rel.split('/');
  return patterns.some((p) => {
    if (p.endsWith('/')) return parts.slice(0, -1).includes(p.slice(0, -1)) && (rel.startsWith(p) || rel.includes('/' + p));
    if (p.includes('*')) return globToRegex(p).test(parts[parts.length - 1]) || globToRegex(p).test(rel);
    return rel === p || parts.includes(p);
  });
}

function apiFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? apiFiles(p) : e.name.endsWith('.js') ? [p] : [];
  });
}

const problems = [];
for (const file of apiFiles(path.join(root, 'api'))) {
  const src = fs.readFileSync(file, 'utf8');
  for (const m of src.matchAll(/require\(\s*['"](\.{1,2}\/[^'"]+)['"]\s*\)/g)) {
    let target = path.resolve(path.dirname(file), m[1]);
    const found = [target, target + '.js', path.join(target, 'index.js')].find((c) => fs.existsSync(c) && fs.statSync(c).isFile());
    const rel = path.relative(root, found || target).split(path.sep).join('/');
    if (!found) problems.push(`${path.relative(root, file)} requires ${m[1]}, which does not exist`);
    else if (ignored(rel)) problems.push(`${path.relative(root, file)} requires ${rel}, which .vercelignore excludes from the deployed function`);
  }
}
assert.deepStrictEqual(problems, [], problems.join('\n'));
// the matcher itself: the files that crashed production are recognised as excluded
assert(ignored('lib/further-reading.js') && ignored('app/page.tsx') && ignored('api/_lib/further-reading.js') === false);
console.log('vercel bundle: every required local file is deployed');

// ---------------------------------------------------------------------------------------------------------------------------------
// Public routes must reach a handler. vercel.json uses "builds", where a function file api/a/b.js is served at /api/a/b.js, and only
// api/a/b/index.js is also served at /api/a/b (measured on production 2026-10-13: /api/version.js was 200 and /api/version was 404 for
// api/version.js, while /api/episodes was 200 for api/episodes/index.js). The "/api/(.*)" route sends /api/version to /api/version, so a
// plain api/version.js was never reachable at the URL DEPLOY.md documents.
const vercel = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));

function route(url) {
  for (const r of vercel.routes) {
    if (!r.src || !r.dest) continue;
    const m = new RegExp('^' + r.src + '$').exec(url);
    if (m) {
      let dest = r.dest;
      for (const [k, v] of Object.entries(m.groups || {})) dest = dest.replace('$' + k, v);
      for (let i = 1; i < m.length; i++) dest = dest.replace('$' + i, m[i]);
      return dest.split('?')[0];
    }
  }
  return null;
}
function servedUrls(relFiles) {
  const urls = new Set();
  for (const f of relFiles) {
    urls.add('/' + f);                                           // api/a/b.js -> /api/a/b.js
    if (path.posix.basename(f) === 'index.js') urls.add('/' + path.posix.dirname(f));   // api/a/b/index.js -> /api/a/b
  }
  return urls;
}
const apiRel = apiFiles(path.join(root, 'api')).map((f) => path.relative(root, f).split(path.sep).join('/'));
const served = servedUrls(apiRel);
for (const publicUrl of ['/api/version', '/episodes/ever-x-1']) {
  const dest = route(publicUrl);
  assert(dest && served.has(dest), `${publicUrl} routes to ${dest}, which no deployed function serves (served: ${[...served].join(', ')})`);
}
// the matcher itself: the layout that returned 404 in production is recognised as unreachable, the fixed one is not
assert(!servedUrls(['api/version.js']).has('/api/version') && servedUrls(['api/version/index.js']).has('/api/version'));
console.log('vercel bundle: public routes reach a handler');
