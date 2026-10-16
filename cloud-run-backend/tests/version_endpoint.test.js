// Run with: node cloud-run-backend/tests/version_endpoint.test.js
const assert = require('assert');
const handler = require('../../api/version/index.js');

function call(env) {
  const saved = { ...process.env };
  for (const k of ['VERCEL_GIT_COMMIT_SHA', 'VERCEL_DEPLOYMENT_ID', 'VERCEL_ENV']) delete process.env[k];
  Object.assign(process.env, env);
  const res = { headers: {}, statusCode: 0, body: null, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.statusCode = c; return this; }, json(b) { this.body = b; return this; } };
  handler({ method: 'GET' }, res);
  process.env = saved;
  return res;
}

let r = call({ VERCEL_GIT_COMMIT_SHA: 'abc123', VERCEL_DEPLOYMENT_ID: 'dpl_1', VERCEL_ENV: 'production' });
assert.strictEqual(r.statusCode, 200);
assert.deepStrictEqual(r.body, { commit: 'abc123', deployment: 'dpl_1', environment: 'production' });
assert.strictEqual(r.headers['Cache-Control'], 'no-store');
r = call({});
assert.deepStrictEqual(r.body, { commit: null, deployment: null, environment: null });
// it exposes nothing else from the environment
assert.deepStrictEqual(Object.keys(call({ SECRET_TOKEN: 'x' }).body).sort(), ['commit', 'deployment', 'environment']);
console.log('version endpoint: ok');
