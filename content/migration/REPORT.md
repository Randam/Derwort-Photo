# WordPress migration inventory — 23 October 2026

The public WordPress REST API reported `X-WP-Total: 72` and `X-WP-TotalPages: 1` for published posts with `per_page=100`. All 72 records are represented in `source-posts.json` and have reviewed rewrites in `../editorial.json`.

The source posts contained 413 inline image references (401 distinct URL strings). Featured images, original portfolio collections and the five homepage carousel photographs were also inventoried. After normalising WordPress size suffixes and deduplicating paths, the complete migration contains **413 unique original image files**. All were downloaded successfully; `media-errors.json` is empty. Each has three independently stored WebP variants. Images shared by several articles are stored once.

Original portfolio URLs retained:

- `/blog/portfolio-items/windmills/`
- `/blog/portfolio-items/zoetermeer/`
- `/blog/portfolio-items/dubai/`

All blog article paths and publication dates are preserved. Titles and paragraphs were rewritten, keeping the original first-person perspective and making the historical context explicit where appropriate. The article modification date reflects the editorial migration on 23 October 2026. The original text and original WordPress modification dates remain in the inventory for comparison.

The former About Me page contained theme placeholder text, stock demonstration imagery and example client logos. These were replaced by the verified photographer introduction from the original homepage. The contact page, comments, spam, administrative links and WordPress presentation wrappers were excluded.

An independent local backup was saved at `~/Documents/Derwort-Photo-WordPress-backup/`. It contains all 413 original image downloads, the full REST exports for posts and pages, and HTML snapshots of the homepage and three portfolio pages. This backup is outside the repository and deployment output.

Verification covers editorial/source coverage; all local links and image references; the three image variants per photograph; one primary heading and canonical URL on each indexable page; valid JSON metadata; all 72 RSS items; sitemap coverage; and removal of the Contact page. The completed build has 317 indexable pages, plus redirects and the custom 404 page.
