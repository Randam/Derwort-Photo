#!/usr/bin/env python3
"""Validate exported routes, local assets, content coverage and structured metadata."""
import argparse, json, re, sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):super().__init__();self.refs=[];self.h1=0;self.canonical=[];self.noindex=False;self.json=[];self.script=False;self.buffer='';self.text=[];self.meta={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='meta':self.meta[a.get('property') or a.get('name')]=a.get('content','')
        if tag=='h1':self.h1+=1
        if tag in ['a','link'] and a.get('href'):self.refs.append(a['href'])
        if tag in ['img','script'] and a.get('src'):self.refs.append(a['src'])
        if tag=='img':
            assert 'alt' in a,'Image without alt text'
            for item in a.get('srcset','').split(','):
                if item.strip():self.refs.append(item.strip().split()[0])
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
        if tag=='meta' and a.get('name')=='robots' and 'noindex' in a.get('content',''):self.noindex=True
        if tag=='script' and a.get('type') in ['application/ld+json','application/json']:self.script=True;self.buffer=''
    def handle_data(self,text):
        if self.script:self.buffer+=text
        else:self.text.append(text)
    def handle_endtag(self,tag):
        if tag=='script' and self.script:self.json.append(json.loads(self.buffer));self.script=False

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='dist');p.add_argument('--base-path',default='');args=p.parse_args();out=ROOT/args.out;base=args.base_path.rstrip('/');errors=[];count=0;indexable=[]
    def exists(ref):
        u=urlsplit(ref)
        if u.scheme or u.netloc or not u.path:return True
        path=unquote(u.path)
        if base and path.startswith(base+'/'):path=path[len(base):]
        f=out/path.lstrip('/')
        return (f/'index.html').exists() if path.endswith('/') else f.is_file()
    for file in out.rglob('*.html'):
        count+=1;page=Page()
        try:page.feed(file.read_text())
        except Exception as exc:errors.append(f'{file.relative_to(out)}: {exc}');continue
        if not page.noindex:
            if page.h1!=1:errors.append(f'{file.relative_to(out)}: expected one h1, got {page.h1}')
            if len(page.canonical)!=1:errors.append(f'{file.relative_to(out)}: missing/duplicate canonical URL')
            indexable.append(page.canonical[0])
            if page.refs.count(base+'/analytics.js')!=1:errors.append(f'{file.relative_to(out)}: missing/duplicate Analytics consent script')
            if 'data-cookie-settings' not in file.read_text():errors.append(f'{file.relative_to(out)}: missing cookie preferences control')
            required=['og:title','og:description','og:url','og:image','og:image:secure_url','og:image:type','og:image:width','og:image:height','og:image:alt','twitter:card','twitter:title','twitter:description','twitter:image','twitter:image:alt']
            if any(not page.meta.get(key) for key in required):errors.append(f'{file.relative_to(out)}: incomplete sharing metadata')
            image=page.meta.get('og:image','');url=urlsplit(image)
            if url.scheme!='https' or url.netloc!='www.derwortphoto.com' or not url.path.startswith('/assets/social/') or not url.path.endswith('.jpg') or not (out/url.path.lstrip('/')).is_file():errors.append(f'{file.relative_to(out)}: missing public sharing JPEG')
            expected={'og:image:type':'image/jpeg','og:image:width':'1200','og:image:height':'630','og:image:secure_url':image,'twitter:image':image,'twitter:card':'summary_large_image'}
            if any(page.meta.get(key)!=value for key,value in expected.items()):errors.append(f'{file.relative_to(out)}: inconsistent sharing image metadata')
        for ref in page.refs:
            if not exists(ref):errors.append(f'{file.relative_to(out)}: missing {ref}')
        # Both embedded gallery data and all search-card destinations must be valid.
        def data_refs(data):
            if isinstance(data,dict):
                for key,value in data.items():
                    if key in ['src','medium','thumb','image','path'] and isinstance(value,str) and value.startswith('/') and not exists(value):errors.append(f'{file.relative_to(out)}: missing data asset {value}')
                    elif isinstance(value,(dict,list)):data_refs(value)
            elif isinstance(data,list):
                for item in data:data_refs(item)
        for data in page.json:data_refs(data)
        text=' '.join(page.text)
        if re.search(r'lorem ipsum|data-story=|wordpress',text,re.I):errors.append(f'{file.relative_to(out)}: template placeholder or WordPress content leaked')
    for url in re.findall(r'url\([\'"]?([^\)\'\"]+)',(out/'style.css').read_text()):
        if not exists(url):errors.append('Missing CSS asset '+url)
    xml=ElementTree.parse(out/'sitemap.xml');locs=[x.text for x in xml.findall('.//{*}loc')]
    if len(locs)!=len(set(locs)):errors.append('Duplicate sitemap URLs')
    if set(indexable)!=set(locs):errors.append('Sitemap does not match indexable pages')
    feed=ElementTree.parse(out/'feed.xml')
    if len(feed.findall('.//item'))!=72:errors.append('RSS does not include all 72 articles')
    source=json.loads((ROOT/'content/migration/source-posts.json').read_text());editorial=json.loads((ROOT/'content/editorial.json').read_text());media=json.loads((ROOT/'content/migration/media.json').read_text())
    if {x['slug'] for x in source}!={x['slug'] for x in editorial}:errors.append('Editorial coverage differs from WordPress')
    for post in source:
        route=out/'blog'/post['slug']/'index.html'
        if not route.exists():errors.append('Missing original article URL '+post['url'])
        elif '"@type": "BlogPosting"' not in route.read_text():errors.append('Missing BlogPosting metadata '+post['slug'])
    if (out/'contact').exists():errors.append('Contact page should be removed')
    for key,m in media.items():
        for variant in ['src','medium','thumb']:
            if not exists(m[variant]):errors.append('Missing photograph '+m[variant])
    if errors:
        print('\n'.join(errors[:80]));print(f'FAILED: {len(errors)} issues');return 1
    print(f'PASS: {count} HTML pages, {len(locs)} canonical URLs, {len(source)} migrated articles, {len(media)} photographs, local links, image variants, fonts, RSS and sitemap.')
    return 0
if __name__=='__main__':sys.exit(main())
