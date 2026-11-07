// A deliberately small fake DOM, enough to RUN the onboarding page scripts (public/onboarding/*.js) in Node with a mocked fetch and fake timers.
// It implements only what those scripts use. It is not a browser: layout, CSS and the CSP are not exercised here.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const PAGES = path.join(__dirname, '..', '..', 'public', 'onboarding');

class TextNode {
  constructor(data) { this.nodeType = 3; this.data = String(data); this.parentNode = null; }
  get textContent() { return this.data; }
}

class El {
  constructor(tag, doc) {
    this.nodeType = 1; this.tag = tag; this.doc = doc; this.children = []; this.parentNode = null; this.attrs = {}; this.listeners = {};
    this.className = ''; this.hidden = false; this.disabled = false; this.checked = false; this.selected = false; this._value = undefined;
  }
  // A <select>'s value is the value of its selected <option> (or the first one), as in a browser, unless it was assigned.
  get value() {
    if (this._value !== undefined) return this._value;
    if (this.tag === 'select') { const o = this.children.filter((c) => c.tag === 'option'); const s = o.find((x) => x.selected) || o[0]; return s ? s._value || '' : ''; }
    return '';
  }
  set value(v) { this._value = String(v); }
  get firstChild() { return this.children[0] || null; }
  appendChild(n) { if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.children.push(n); return n; }
  removeChild(n) { const i = this.children.indexOf(n); if (i >= 0) this.children.splice(i, 1); n.parentNode = null; return n; }
  insertBefore(n, ref) {
    if (n.parentNode) n.parentNode.removeChild(n);
    const i = ref ? this.children.indexOf(ref) : -1;
    n.parentNode = this;
    if (i < 0) this.children.push(n); else this.children.splice(i, 0, n);
    return n;
  }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === 'id') this.doc.ids[v] = this; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  fire(type) { (this.listeners[type] || []).forEach((fn) => fn({ target: this, preventDefault() {} })); }
  contains(n) { for (let x = n; x; x = x.parentNode) if (x === this) return true; return false; }
  get textContent() { return this.children.map((c) => c.textContent).join(''); }
  set textContent(v) { this.children.forEach((c) => { c.parentNode = null; }); this.children = []; if (String(v) !== '') this.appendChild(new TextNode(v)); }
  // test helpers
  click() {
    if (this.disabled) return;
    if (this.attrs.type === 'radio') this.doc.eachEl((e) => { if (e.attrs.type === 'radio' && e.attrs.name === this.attrs.name) e.checked = false; });
    if (this.attrs.type === 'radio' || this.attrs.type === 'checkbox') { this.checked = this.attrs.type === 'radio' ? true : !this.checked; this.fire('change'); }
    this.fire('click');
  }
  type(text) { this.value = text; this.fire('input'); }
  walk(fn) { fn(this); this.children.forEach((c) => (c.walk ? c.walk(fn) : fn(c))); }
}

class Doc {
  constructor() { this.ids = {}; this.body = new El('body', this); this.activeElement = null; this.hidden = false; }
  createElement(tag) { return new El(tag, this); }
  createTextNode(t) { return new TextNode(t); }
  getElementById(id) { return this.ids[id] || null; }
  eachEl(fn) { this.body.walk((n) => { if (n.nodeType === 1) fn(n); }); }
  all() { const out = []; this.eachEl((e) => out.push(e)); return out; }
}

// Creates one element per id="..." in the page HTML (nesting is ignored; the scripts only look elements up by id), with hidden/type/name/value/checked taken from the tag.
function loadPage(htmlFile, doc) {
  const html = fs.readFileSync(path.join(PAGES, htmlFile), 'utf8');
  const re = /<(\w+)\b([^>]*?)\sid="([^"]+)"([^>]*)>/g;
  let m;
  while ((m = re.exec(html))) {
    const el = doc.createElement(m[1]);
    const attrs = m[2] + ' ' + m[4];
    el.setAttribute('id', m[3]);
    if (/\shidden(\s|$|>)/.test(attrs + ' ')) el.hidden = true;
    for (const k of ['type', 'name', 'value']) { const a = new RegExp('\\s' + k + '="([^"]*)"').exec(attrs); if (a) { el.setAttribute(k, a[1]); if (k === 'value') el.value = a[1]; } }
    if (/\schecked(\s|$|>)/.test(attrs + ' ')) el.checked = true;
    doc.body.appendChild(el);
  }
}

// Fake timers: setTimeout/setInterval only record; tests run them with flushTimeouts() / tickIntervals().
function makeTimers() {
  let n = 0;
  const t = { timeouts: new Map(), intervals: new Map() };
  return {
    setTimeout: (fn) => { n += 1; t.timeouts.set(n, fn); return n; }, clearTimeout: (id) => { t.timeouts.delete(id); },
    setInterval: (fn) => { n += 1; t.intervals.set(n, fn); return n; }, clearInterval: (id) => { t.intervals.delete(id); },
    flushTimeouts() { const fns = [...t.timeouts.values()]; t.timeouts.clear(); fns.forEach((f) => f()); return fns.length; },
    tickIntervals() { [...t.intervals.values()].forEach((f) => f()); },
    pending: () => t.timeouts.size,
  };
}

async function settle(rounds = 8) { for (let i = 0; i < rounds; i += 1) await new Promise((r) => setImmediate(r)); }

// Runs common.js and then the page script in a fresh context. `route(method, path, body)` returns {status, data} (or a Promise of it).
function run(pageHtml, scripts, { search = '', token = 'tok', route, confirmAnswer = true }) {
  const doc = new Doc();
  loadPage(pageHtml, doc);
  const timers = makeTimers();
  const calls = [];
  const confirms = [];   // every question the page asked through confirm(); the answer is `confirmAnswer` (true or false)
  const sandbox = {
    document: doc, location: { search }, console, Promise, JSON, Object, Array, String, Number, Date, Math, encodeURIComponent, decodeURIComponent, RegExp, Error,
    confirm: (q) => { confirms.push(q); return typeof confirmAnswer === 'function' ? confirmAnswer(q) : confirmAnswer; },
    localStorage: { getItem: (k) => (k === 'subscriber' && token ? JSON.stringify({ session_token: token }) : null) },
    setTimeout: timers.setTimeout, clearTimeout: timers.clearTimeout, setInterval: timers.setInterval, clearInterval: timers.clearInterval,
    fetch: (url, init) => {
      const p = String(url).replace(/^https:\/\/[^/]+/, '');
      const body = init && init.body ? JSON.parse(init.body) : undefined;
      calls.push({ method: (init && init.method) || 'GET', path: p, body, token: init && init.headers && init.headers['X-Subscriber-Token'] });
      return Promise.resolve(route((init && init.method) || 'GET', p, body)).then((r) => ({ ok: r.status >= 200 && r.status < 300, status: r.status, json: () => Promise.resolve(r.data) }));
    },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  for (const s of scripts) vm.runInContext(fs.readFileSync(path.join(PAGES, s), 'utf8'), sandbox, { filename: s });
  return { doc, timers, calls, confirms, sandbox, $: (id) => doc.getElementById(id) };
}

// Everything in the tree that is an element (to prove a hostile string never became markup).
function elementTags(doc) { return doc.all().map((e) => e.tag); }

module.exports = { run, settle, elementTags, El, Doc };
