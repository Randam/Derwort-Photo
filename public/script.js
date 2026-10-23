'use strict';
const photoData = document.querySelector('#photo-data');
const photographs = photoData ? JSON.parse(photoData.textContent) : [];
let heroIndex = 0;
let lightboxIndex = 0;
const heroImage = document.querySelector('#hero-image');
function setHero(direction) {
  if (!heroImage || !photographs.length) return;
  heroIndex = (heroIndex + direction + photographs.length) % photographs.length;
  const photo = photographs[heroIndex];
  heroImage.src = photo.medium;
  const widths = [640, 1200, 2400].map(size => Math.round(photo.width * Math.min(1, size / Math.max(photo.width, photo.height))));
  heroImage.srcset = [photo.thumb, photo.medium, photo.src].map((source, i) => `${source} ${widths[i]}w`).join(', ');
  heroImage.sizes = '100vw';
  heroImage.alt = photo.alt;
  document.querySelector('#hero-title').textContent = photo.title;
  document.querySelector('#hero-country').textContent = photo.place;
  document.querySelector('#hero-number').textContent = `${String(heroIndex + 1).padStart(2, '0')} / ${String(photographs.length).padStart(2, '0')}`;
}
document.querySelector('#previous')?.addEventListener('click', () => setHero(-1));
document.querySelector('#next')?.addEventListener('click', () => setHero(1));
document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-filter]').forEach(other => {
    other.classList.toggle('active', other === button);
    other.setAttribute('aria-pressed', String(other === button));
  });
  document.querySelectorAll('.gallery figure').forEach(figure => {
    figure.hidden = button.dataset.filter !== 'all' && figure.dataset.category !== button.dataset.filter;
  });
}));
const lightbox = document.querySelector('#lightbox');
function showPhoto(index) {
  lightboxIndex = (index + photographs.length) % photographs.length;
  const photo = photographs[lightboxIndex];
  const image = document.querySelector('#lightbox-image');
  image.src = photo.src;
  image.alt = photo.alt || photo.title;
  document.querySelector('#lightbox-title').textContent = photo.title;
  document.querySelector('#lightbox-detail').textContent = photo.detail || 'Photograph by Jeroen Derwort';
  document.querySelector('#lightbox-position').textContent = `${lightboxIndex + 1} / ${photographs.length}`;
}
document.querySelectorAll('[data-index]').forEach(link => link.addEventListener('click', event => {
  // Keep the image link usable without JavaScript and with normal browser modifiers.
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  if (!lightbox || !photographs.length) return;
  event.preventDefault();
  showPhoto(Number(link.dataset.index));
  lightbox.showModal();
}));
lightbox?.querySelector('.close').addEventListener('click', () => lightbox.close());
lightbox?.querySelector('.lightbox-prev').addEventListener('click', () => showPhoto(lightboxIndex - 1));
lightbox?.querySelector('.lightbox-next').addEventListener('click', () => showPhoto(lightboxIndex + 1));
lightbox?.addEventListener('click', event => { if (event.target === lightbox) lightbox.close(); });
document.addEventListener('keydown', event => {
  if (!lightbox?.open) return;
  if (event.key === 'ArrowRight') { event.preventDefault(); showPhoto(lightboxIndex + 1); }
  if (event.key === 'ArrowLeft') { event.preventDefault(); showPhoto(lightboxIndex - 1); }
});
let touchStart = null;
lightbox?.addEventListener('touchstart', event => { touchStart = event.touches[0].clientX; }, { passive: true });
lightbox?.addEventListener('touchend', event => {
  if (touchStart === null) return;
  const change = event.changedTouches[0].clientX - touchStart;
  if (Math.abs(change) > 60) showPhoto(lightboxIndex + (change < 0 ? 1 : -1));
  touchStart = null;
}, { passive: true });
const journalData = document.querySelector('#journal-data');
if (journalData) {
  const posts = JSON.parse(journalData.textContent);
  const search = document.querySelector('#journal-search');
  const category = document.querySelector('#journal-category');
  const results = document.querySelector('#journal-results');
  const status = document.querySelector('#search-status');
  const pagination = document.querySelector('.pagination');
  const initialCards = [...results.children];
  const initialStatus = status.textContent;
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }
  function makeCard(post) {
    const card = element('article');
    const link = element('a', 'story-image');
    link.href = post.path;
    const image = element('img');
    image.src = post.image;
    image.alt = post.title;
    image.loading = 'lazy';
    image.width = 640;
    image.height = 427;
    link.append(image);
    const meta = element('p', 'story-meta', post.category.toUpperCase());
    const time = element('time', '', post.date.toUpperCase());
    time.dateTime = post.iso;
    meta.append(time);
    const heading = element('h3');
    const titleLink = element('a', '', post.title);
    titleLink.href = post.path;
    const arrow = element('span', '', '↗');
    arrow.setAttribute('aria-hidden', 'true');
    titleLink.append(arrow);
    heading.append(titleLink);
    card.append(link, meta, heading, element('p', '', post.description));
    return card;
  }
  function filter() {
    const query = normalize(search.value.trim());
    const selectedCategory = category.value;
    if (!query && !selectedCategory) {
      results.replaceChildren(...initialCards);
      status.textContent = initialStatus;
      pagination.hidden = false;
      return;
    }
    const matches = posts.filter(post => (!selectedCategory || post.categories.includes(selectedCategory)) &&
      normalize([post.title, post.description, ...post.tags].join(' ')).includes(query));
    results.replaceChildren(...matches.map(makeCard));
    status.textContent = `${matches.length} photo ${matches.length === 1 ? 'story' : 'stories'} found`;
    pagination.hidden = true;
    if (!matches.length) results.append(element('p', 'no-results', 'No stories found. Try another place or subject, or choose a different category.'));
  }
  search.addEventListener('input', filter);
  category.addEventListener('change', filter);
  const query = new URLSearchParams(location.search).get('q');
  if (query) { search.value = query; filter(); }
}
const year = document.querySelector('#year');
if (year) year.textContent = new Date().getFullYear();
