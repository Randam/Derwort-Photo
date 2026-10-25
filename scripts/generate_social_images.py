#!/usr/bin/env python3
"""Regenerate committed sharing JPEGs. Optional maintenance tool; requires Pillow."""
from PIL import Image, ImageOps
from build import Builder, ROOT, normalized, social_path


def main():
    builder = Builder(ROOT / 'dist', '')
    sources = {builder.features[0]['src']}
    sources.update(builder.cover(post)['src'] for post in builder.posts)
    sources.update(builder.media[normalized(items[0]['src'])]['src'] for items in builder.portfolio.values())
    for source in sorted(sources):
        with Image.open(ROOT / 'public' / source.lstrip('/')) as original:
            # Preserve the complete photograph, including portrait compositions.
            photo = ImageOps.contain(original.convert('RGB'), (1200, 630), Image.Resampling.LANCZOS)
            card = Image.new('RGB', (1200, 630), '#f5f3ee')
            card.paste(photo, ((1200 - photo.width) // 2, (630 - photo.height) // 2))
            target = ROOT / 'public' / social_path(source).lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            card.save(target, 'JPEG', quality=88, optimize=True, progressive=True)
    print(f'Generated {len(sources)} sharing JPEGs (1200 × 630).')


if __name__ == '__main__':
    main()
