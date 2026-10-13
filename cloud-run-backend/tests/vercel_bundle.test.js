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
