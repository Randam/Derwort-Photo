// Consent regression tests without a browser or external network requests.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('public/analytics.js', 'utf8');
function run({ saved, hostname = 'www.derwortphoto.com', blocked = false } = {}) {
  const scripts = [], deleted = [], storage = new Map(), events = {};
  if (saved) storage.set('derwort-photo-analytics-v1', JSON.stringify(saved));
  const element = () => ({ hidden: true, dataset: {}, handlers: {}, setAttribute() {}, addEventListener(type, fn) { this.handlers[type] = fn; }, focus() { this.focused = true; } });
  const denied = element(), granted = element(), settings = element(), panel = element();
  denied.dataset.consent = 'denied'; granted.dataset.consent = 'granted';
  panel.querySelectorAll = () => [denied, granted];
  panel.querySelector = selector => selector.includes('"granted"') ? granted : denied;
  let reloads = 0;
  const document = {
    createElement: tag => tag === 'section' ? panel : {},
    body: { append() {} }, head: { append: script => scripts.push(script) },
    querySelector: () => settings, querySelectorAll: () => [settings],
    get cookie() { return '_ga=test; _ga_7LYYWF922P=session; necessary=keep'; },
    set cookie(value) { deleted.push(value); }
  };
  const context = {
    document, location: { hostname, reload() { reloads++; } },
    localStorage: { getItem(key) { if (blocked) throw Error('blocked'); return storage.get(key) || null; }, setItem(key, value) { if (blocked) throw Error('blocked'); storage.set(key, value); } },
    window: { addEventListener(type, fn) { events[type] = fn; } }, Date
  };
  vm.runInNewContext(source, context);
  return { scripts, deleted, panel, settings, denied, granted, storage, context, events, reloads: () => reloads };
}
const fresh = run();
assert.equal(fresh.scripts.length, 0, 'no Google request before consent');
assert.equal(fresh.panel.hidden, false);
fresh.denied.handlers.click();
assert.equal(fresh.scripts.length, 0, 'declining never loads Google');
assert.equal(fresh.panel.hidden, true);
assert(fresh.deleted.every(cookie => !cookie.startsWith('necessary=')));
fresh.settings.handlers.click();
assert.equal(fresh.panel.hidden, false);
fresh.granted.handlers.click();
assert.equal(fresh.scripts.length, 1);
assert.equal(fresh.scripts[0].src, 'https://www.googletagmanager.com/gtag/js?id=G-7LYYWF922P');
assert.equal(fresh.context.window.dataLayer.filter(command => command[0] === 'config').length, 1, 'one automatic page view per load');
fresh.granted.handlers.click();
assert.equal(fresh.scripts.length, 1, 'repeat acceptance never duplicates the tag');
fresh.denied.handlers.click();
assert.equal(fresh.context.window['ga-disable-G-7LYYWF922P'], true);
assert.equal(fresh.reloads(), 1, 'withdrawal stops the loaded tag by reloading');
assert.equal(run({ saved: { value: 'granted', time: Date.now() } }).scripts.length, 1);
assert.equal(run({ saved: { value: 'denied', time: Date.now() } }).scripts.length, 0);
assert.equal(run({ saved: { value: 'granted', time: 0 } }).scripts.length, 0, 'expired consent requires a fresh choice');
const local = run({ hostname: 'localhost' }); local.granted.handlers.click(); assert.equal(local.scripts.length, 0);
const blocked = run({ blocked: true }); blocked.granted.handlers.click(); assert.equal(blocked.scripts.length, 1, 'storage restrictions do not break the choice');
fresh.events.storage({ key: 'derwort-photo-analytics-v1' }); assert.equal(fresh.reloads(), 2, 'changes propagate to other open tabs');
console.log('PASS: consent gating, grant/decline, persistence, expiry, withdrawal, cookie cleanup, local previews and cross-tab changes.');
