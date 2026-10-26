'use strict';
(() => {
  const measurementId = 'G-7LYYWF922P';
  const storageKey = 'derwort-photo-analytics-v1';
  const lifetime = 180 * 24 * 60 * 60 * 1000;
  const production = ['www.derwortphoto.com', 'derwortphoto.com'].includes(location.hostname);
  let loaded = false;
  let choice;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved && ['granted', 'denied'].includes(saved.value) && Date.now() - saved.time < lifetime) choice = saved.value;
  } catch (_) { /* A blocked storage API must not prevent a visitor from choosing. */ }

  const panel = document.createElement('section');
  panel.className = 'analytics-consent';
  panel.setAttribute('aria-label', 'Analytics cookie preferences');
  panel.innerHTML = '<div><h2>A little insight, with your permission</h2><p>May we use Google Analytics cookies to understand which photographs and stories you enjoy? Google receives information about your visit. Your choice is saved for six months and can be changed in Cookie settings. <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener noreferrer">How Google uses data ↗</a></p></div><div class="consent-actions"><button type="button" data-consent="denied">Decline analytics</button><button type="button" data-consent="granted">Allow analytics</button></div>';
  panel.hidden = Boolean(choice);
  document.body.append(panel);

  function enable() {
    if (loaded || !production) return;
    loaded = true;
    window['ga-disable-' + measurementId] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('consent', 'default', { analytics_storage: 'denied', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
    window.gtag('consent', 'update', { analytics_storage: 'granted' });
    window.gtag('js', new Date());
    window.gtag('config', measurementId, { allow_google_signals: false, allow_ad_personalization_signals: false });
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.append(script);
  }
  function clearAnalyticsCookies() {
    const domains = ['', location.hostname, '.' + location.hostname, '.derwortphoto.com', 'derwortphoto.com'];
    document.cookie.split(';').forEach(cookie => {
      const name = cookie.trim().split('=')[0];
      if (!/^_ga(?:_|$)|^_gid$|^_gat(?:_|$)/.test(name)) return;
      domains.forEach(domain => { document.cookie = name + '=; Max-Age=0; Path=/; SameSite=Lax' + (domain ? '; Domain=' + domain : ''); });
    });
  }
  function choose(value) {
    choice = value;
    try { localStorage.setItem(storageKey, JSON.stringify({ value, time: Date.now() })); } catch (_) { /* Keep the choice for this page when storage is unavailable. */ }
    panel.hidden = true;
    if (value === 'granted') enable();
    else {
      window['ga-disable-' + measurementId] = true;
      clearAnalyticsCookies();
      // A new document stops the already-loaded tag after consent is withdrawn.
      if (loaded) location.reload();
    }
    document.querySelector('[data-cookie-settings]')?.focus({ preventScroll: true });
  }
  panel.querySelectorAll('[data-consent]').forEach(button => button.addEventListener('click', () => choose(button.dataset.consent)));
  document.querySelectorAll('[data-cookie-settings]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => {
      panel.hidden = false;
      panel.querySelector('[data-consent="' + (choice || 'denied') + '"]').focus();
    });
  });
  window.addEventListener('storage', event => {
    if (event.key === storageKey) location.reload();
  });
  if (choice === 'granted') enable();
  else clearAnalyticsCookies();
})();
