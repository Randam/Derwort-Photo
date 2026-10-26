# Derwort Photo

A photography-first, static replacement for [www.derwortphoto.com](https://www.derwortphoto.com). The approved design uses a warm paper background, quiet typography and large photographs. No WordPress installation, database, JavaScript framework or build service is required.

## Build and preview

Python 3.12 or newer is sufficient. There are no build dependencies to install.

```sh
python3 scripts/build.py
python3 scripts/verify.py
python3 -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Visit `http://127.0.0.1:4173/`. Upload **the contents of `dist/`** to a static web host. Generated files are excluded from Git. GitHub Actions builds and verifies the website after every push, then publishes successful `main` builds to **GitHub Pages**. Pull requests are verified without deploying. The custom production domain is **https://www.derwortphoto.com**; Cloudflare manages DNS and migration redirects.

For a host that serves this repository under a project subdirectory:

```sh
python3 scripts/build.py --out /tmp/derwort-photo-preview --base-path /Derwort-Photo
python3 scripts/verify.py --out /tmp/derwort-photo-preview --base-path /Derwort-Photo
```

This adjusts local links, image data, fonts and redirects for the subdirectory. Production canonical URLs intentionally refer to `https://www.derwortphoto.com`.

## Migrated content

- All **72 published WordPress blog posts**, with the original `/blog/<slug>/` paths and publication dates.
- All articles rewritten in English for readability, clearer place names and more useful search descriptions. Old practical advice is presented as a dated personal visit, rather than a current recommendation.
- **413 unique photographs**, including the five original homepage carousel images and the Windmills, Zoetermeer and Dubai portfolio collections.
- Local WebP images in 640, 1200 and 2400-pixel variants, preserving image proportions. The long edge is capped at each size; portraits therefore have smaller width descriptors. The original full-resolution photographs are not needed by the deployed website.
- A paginated Journal, browser-local search across all stories, category filters, category/tag archives, related articles and accessible photograph dialogs with keyboard navigation and mobile swipe support.
- Locally hosted fonts and their OFL licences; no external font requests, contact form or WordPress runtime requests.
- Canonical URLs, Open Graph metadata, `BlogPosting` structured data, `sitemap.xml`, `robots.txt`, RSS at `/feed.xml` and a custom 404 page.
- The Contact page is removed. Instagram and 500px remain available in the About section.

The migration inventory and source text are retained in `content/migration/`. This is a content migration, not a WordPress database backup. Plugin settings, users, comments, spam, and unused theme demonstration content are deliberately not part of the new website.

## Editing

- `content/editorial.json`: reviewed titles and article paragraphs, keyed by the original slug.
- `content/migration/source-posts.json`: original dates, image references, taxonomy terms and source text.
- `content/migration/media.json`: local asset variants, dimensions and original source URLs.
- `content/migration/portfolio.json`: original portfolio selections.
- `templates/home.html`: approved homepage layout.
- `public/style.css` and `public/script.js`: shared design and interactions.
- `scripts/build.py`: static page generation, shared navigation, article galleries and SEO output.

After editing, rebuild and run the verifier. Every article and its photographs remain accessible without JavaScript; JavaScript adds the photo viewer, carousel controls, filtering and search. Pagination provides a complete alternative to search.

The optional one-time importer, `scripts/migrate_media.py`, requires Pillow. It can reconstruct missing web image variants from the inventoried original URLs; it is not invoked during ordinary builds. Pass `--backup-directory /path/to/originals` to retain downloaded originals outside this repository.

Social link previews use committed 1200 × 630 JPEGs in `public/assets/social/`, with matching Open Graph and Twitter Card metadata. The homepage uses the Zaanse Schans photograph; articles and collections use their own cover photograph. The complete composition is preserved on a neutral background. After changing cover photographs, run `python3 scripts/generate_social_images.py` (requires Pillow), commit the generated JPEGs, then rebuild and verify. Ordinary builds need no image-processing dependencies.

## Hosting and URL continuity

Production uses GitHub Pages with `www.derwortphoto.com` configured in the repository Pages settings. Both `www.derwortphoto.com` and the apex `derwortphoto.com` point to `randam.github.io` through Cloudflare. The apex redirects to the canonical `www` hostname. A successful push to `main` automatically updates the live site.

The existing 72 article URLs, three portfolio item URLs, category/tag archive paths and `/portfolio/` are real generated pages. `/home/`, `/about-me/`, the former author archive and homepage pagination have fallback HTML redirects and host redirect rules. The Contact URL returns 404.

`dist/_redirects` contains HTTP 301 rules for hosts that support this format, including the old `/files/...` media links and WordPress RSS paths. `dist/.htaccess` provides Apache redirect rules. Preserve these dotfiles when deploying. Plain static servers use the fallback HTML redirects for moved pages; GitHub Pages does not interpret `_redirects`, `_headers` or `.htaccess`. On hosts without HTTP redirects, existing shared media URLs and old feed URLs require host-level routing if they must remain compatible.

Cloudflare Bulk Redirects provides the HTTP 301 responses that GitHub Pages does not implement. The account list is `derwort_photo_legacy_redirects`; its entries cover both production hostnames. Generate its API import file after a build with `python3 scripts/export_cloudflare_redirects.py` (`dist/cloudflare-redirects.json`). It includes the legacy image sizes found in the original articles, moved pages and feeds. Update this list if migration mappings change. Redirects require the Cloudflare proxy to remain enabled.

`public/CNAME` records the custom domain in the source. GitHub Actions deployments also require the custom domain to be configured in repository Settings → Pages. TLS is terminated at Cloudflare with a verified HTTPS connection to GitHub Pages. The independent WordPress and pre-migration DNS backups remain outside this repository.

## Copyright

All photographs and authored content © Jeroen Derwort. All rights reserved. Font licences are included in `public/assets/fonts/`. The presence of photographs in this repository does not grant a reuse licence.

## Google Analytics

The production website uses GA4 property `560833505` and the Derwort Photo web stream (`G-7LYYWF922P`) in the existing Derwort Media account. `public/analytics.js` loads the Google tag only after explicit consent (basic Consent Mode). Advertising storage, ad user data, ad personalization and Google signals are disabled. The choice is stored locally for 180 days and can be changed through Cookie settings in the footer. Declining deletes Analytics cookies; withdrawing an earlier grant reloads the page to stop the loaded tag. Changes also propagate to other open tabs. Google Analytics does not load on local previews.

The Google tag sends the normal page view for each page load; enhanced measurement is managed in the web stream settings. Verify collection in the property's Realtime report after allowing analytics. Regular reports can take longer to populate.
