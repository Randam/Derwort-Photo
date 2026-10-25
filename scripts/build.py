#!/usr/bin/env python3
"""Build the dependency-free Derwort Photo website from reviewed content."""
import argparse, calendar, html, json, math, re, shutil, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.sax.saxutils import escape as xml
ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://www.derwortphoto.com'
FEATURE_TITLES=['Zaanse Schans','Lighthouse Texel','Senhor da Pedra','Under the northern lights','Wonderful light']
FEATURE_PLACES=['The Netherlands','The Netherlands','Portugal','After dark','Woodland']
FEATURE_DETAILS=['26 August 2017 · 21 mm · ƒ/8 · ISO 100 · 13 s','8 October 2017 · 16 mm · ƒ/6.3 · ISO 100 · 1/25 s','13 August 2018 · 35 mm · ƒ/7.1 · ISO 320 · 6 s','28 February 2017 · 28 mm · ƒ/2 · ISO 1000 · 13 s','18 October 2017 · 101 mm · ƒ/5.6 · ISO 2500 · 1/160 s']
def load(path):return json.loads((ROOT/path).read_text())
def esc(s):return html.escape(str(s),quote=True)
def normalized(url):return re.sub(r'-\d+x\d+(?=\.[^.]+$)','',unquote(urlsplit(html.unescape(url)).path))
def date(s):
    d=datetime.fromisoformat(s);return f'{d.day} {calendar.month_name[d.month]} {d.year}'
def excerpt(p):
    text=p['paragraphs'][0]
    if len(text)<=165:return text
    return text[:162].rsplit(' ',1)[0]+ '…'
def json_script(value):return json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
def post_path(p):return '/blog/'+p['slug']+'/'
def social_path(source):return '/assets/social/'+source.rsplit('/',1)[-1].removesuffix('-2400.webp')+'.jpg'
class Builder:
    def __init__(self,out,base):
        self.out=out;self.base=base.rstrip('/');self.urls={};self.redirects={}
        self.media=load('content/migration/media.json')
        raw=load('content/migration/source-posts.json');ed=load('content/editorial.json')
        assert len(raw)==len(ed)==72,'Expected all 72 WordPress posts'
        lookup={x['slug']:x for x in ed};assert len(lookup)==len(raw)
        for p in raw:
            p['categories']=[html.unescape(c).replace('Geen categorie','Uncategorised') for c in p['categories']]
            for t in p['terms']:t['name']=html.unescape(t['name']).replace('Geen categorie','Uncategorised')
        self.posts=[dict(p,**lookup[p['slug']]) for p in raw]
        self.portfolio=load('content/migration/portfolio.json')
        features=load('content/migration/features.json')
        self.features=[dict(self.media[path],title=FEATURE_TITLES[i],place=FEATURE_PLACES[i],detail=FEATURE_DETAILS[i],alt=FEATURE_TITLES[i]) for i,path in enumerate(features.values())]
    def local(self,text):
        if not self.base:return text
        text=re.sub(r'((?:href|src|action)=["\'])/(?!/)',lambda m:m[1]+self.base+'/',text)
        text=re.sub(r'(srcset=["\'])([^"\']+)',lambda m:m[1]+re.sub(r'(^|,\s*)/(?!/)',lambda x:x[1]+self.base+'/',m[2]),text)
        # Data used by the shared browser script also respects a project subdirectory.
        text=text.replace('content="0;url=/','content="0;url='+self.base+'/')
        text=text.replace('"/assets/','"'+self.base+'/assets/').replace('"/blog/','"'+self.base+'/blog/')
        return text
    def write(self,path,text,sitemap=True):
        target=self.out/path.lstrip('/')
        if path.endswith('/'):target=target/'index.html'
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(self.local(text))
        if sitemap:self.urls[path]=True
    def media_for(self,p):
        photos=[];seen=set()
        for i in p['images']:
            key=normalized(i['src'])
            if key in seen:continue
            seen.add(key);m=dict(self.media[key])
            title=re.split(r'\s+(?:ILCE|SLT|SONY)\b|\|',i.get('alt') or i.get('title') or '')[0].strip()
            if not title or re.match(r'^DSC\d+',title,re.I):title=m['caption'] or p['title'].split(':')[0]
            m['title']=title;m['alt']=title+' — '+p['title'].split(':')[0];m['detail']='Photograph by Jeroen Derwort';photos.append(m)
        return photos
    def cover(self,p):return self.media[normalized(p['featured'])] if p.get('featured') else self.media_for(p)[0]
    def image(self,m,alt='',size='medium',lazy=True,sizes='(max-width: 540px) 86vw, 44vw'):
        w,h=m['width'],m['height'];scale=min(1,2400/max(w,h));w,h=round(w*scale),round(h*scale)
        # Descriptor width follows the rendered width, including portrait photographs.
        ws=[round(m['width']*min(1,n/max(m['width'],m['height']))) for n in [640,1200,2400]]
        srcset=', '.join(f'{m[k]} {n}w' for k,n in zip(['thumb','medium','src'],ws))
        return f'<img src="{m[size]}" srcset="{srcset}" sizes="{sizes}" width="{w}" height="{h}" alt="{esc(alt or m.get("caption") or "Photograph by Jeroen Derwort")}" '+('loading="lazy"' if lazy else 'fetchpriority="high"')+' decoding="async">'
    def head(self,title,description,path,image=None,article=None):
        canonical=ORIGIN+path;source=image or self.features[0]['src']
        image=ORIGIN+social_path(source)
        photo=next(m for m in self.media.values() if m['src']==source)
        image_alt=photo.get('caption') or (title if source!=self.features[0]['src'] else self.features[0]['alt'])
        image_alt+=' — photograph by Jeroen Derwort'
        data={'@context':'https://schema.org','@type':'BlogPosting' if article else 'WebPage','headline' if article else 'name':title,'description':description,'url':canonical,'inLanguage':'en','author':{'@type':'Person','name':'Jeroen Derwort','url':ORIGIN+'/#about'},'image':image}
        if article:data.update(datePublished=article['date']+'+02:00' if 4<=int(article['date'][5:7])<=10 else article['date']+'+01:00',dateModified=article['modified'][:10],mainEntityOfPage=canonical)
        # WordPress timestamps are local Amsterdam times, including historical DST.
        if article:
            from zoneinfo import ZoneInfo
            data['datePublished']=datetime.fromisoformat(article['date']).replace(tzinfo=ZoneInfo('Europe/Amsterdam')).isoformat()
            data['dateModified']='2026-10-23'
        return f'''<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Derwort Photo</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#f5f3ee"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="Derwort Photo"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}"><meta property="og:image:secure_url" content="{image}"><meta property="og:image:type" content="image/jpeg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{esc(image_alt)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{image}"><meta name="twitter:image:alt" content="{esc(image_alt)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/style.css"><link rel="alternate" type="application/rss+xml" title="Derwort Photo Journal" href="/feed.xml"><script src="/script.js" defer></script><script type="application/ld+json">{json_script(data)}</script>'''
    def header(self):return '''<a class="skip" href="#main">Skip to content</a><header class="header"><a class="brand" href="/" aria-label="Derwort Photo home">DERWORT<span>PHOTO</span><i></i></a><nav aria-label="Main navigation"><a href="/#photographs">Photographs</a><a href="/blog/">Journal</a><a href="/#about">About</a></nav><a class="header-social" href="https://www.instagram.com/derwortphoto/" target="_blank" rel="noopener noreferrer">Instagram <span>↗</span></a></header>'''
    def footer(self):return '''<footer><a class="brand" href="/">DERWORT<span>PHOTO</span><i></i></a><p>© <span id="year">2026</span> Jeroen Derwort. All rights reserved.</p><a href="#main">Back to top ↑</a></footer>'''
    def lightbox(self,photos):return '''<dialog id="lightbox" aria-labelledby="lightbox-title"><button class="close" aria-label="Close photograph">×</button><button class="lightbox-prev" aria-label="Previous photograph">←</button><img id="lightbox-image" alt=""><button class="lightbox-next" aria-label="Next photograph">→</button><div class="lightbox-caption"><h2 id="lightbox-title"></h2><p id="lightbox-detail"></p><p id="lightbox-position" aria-live="polite"></p></div></dialog>'''+f'<script type="application/json" id="photo-data">{json_script(photos)}</script>'
    def page(self,title,description,path,body,photos=None,image=None,article=None):
        self.write(path,'<!doctype html><html lang="en"><head>'+self.head(title,description,path,image,article)+'</head><body>'+self.header()+body+self.footer()+self.lightbox(photos or [])+'</body></html>')
    def card(self,p):
        category=p['categories'][0] if p['categories'] else 'Photography'
        return f'''<article><a class="story-image" href="{post_path(p)}">{self.image(self.cover(p),p['title'],size='thumb',sizes='(max-width:540px) 86vw, 29vw')}</a><p class="story-meta">{esc(category.upper())}<time datetime="{p['date'][:10]}">{date(p['date']).upper()}</time></p><h3><a href="{post_path(p)}">{esc(p['title'])}<span aria-hidden="true">↗</span></a></h3><p>{esc(excerpt(p))}</p></article>'''
    def home(self):
        s=(ROOT/'templates/home.html').read_text()
        s=re.sub(r'<head>.*?</head>','<head>'+self.head('Landscape & Travel Photography by Jeroen Derwort','Landscape, nature and travel photography by Jeroen Derwort. Explore Dutch landscapes, city scenes and photo stories from around the world.','/')+'</head>',s,flags=re.S)
        s=re.sub(r'<a class="skip".*?</header>',self.header(),s,flags=re.S)
        s=re.sub(r'<footer>.*?</footer>',self.footer(),s,flags=re.S)
        s=s[:s.index('<dialog id="lightbox"')]+self.lightbox(self.features)+'</body></html>'
        s=re.sub(r'<div class="stories">.*?</div></section>',lambda m:'<div class="stories">'+''.join(self.card(p) for p in self.posts[:3])+'</div><a class="text-link journal-all" href="/blog/">Explore all 72 photo stories <span>↗</span></a></section>',s,flags=re.S)
        for i,(old,m) in enumerate(zip(['zaanse-schans','texel','senhor-da-pedra','night','wonderful-light'],self.features)):
            s=s.replace('assets/'+old+'.jpg',m['medium'])
        s=s.replace('src="/assets/photos/', 'src="/assets/photos/')
        s=re.sub(r'<button class="photo" data-index="(\d)" aria-label="([^"]+)">(.*?)</button>',lambda m:f'<a class="photo" data-index="{m[1]}" href="{self.features[int(m[1])]["src"]}" aria-label="{m[2]}">{m[3]}</a>',s,flags=re.S)
        # Add responsive image variants without disturbing the approved layout.
        for m in self.features:
            s=re.sub(r'<img ([^>]*?)src="'+re.escape(m['medium'])+r'"[^>]*>',lambda match:self.image(m,re.search(r'alt="([^"]*)"',match[0])[1],lazy='hero-image' not in match[0],sizes='100vw').replace('<img ','<img id="hero-image" ' if 'hero-image' in match[0] else '<img ',1),s)
        s=s.replace('href="favicon.svg"','href="/favicon.svg"')
        self.write('/',s)
    def gallery(self,photos):
        return '<div class="article-gallery">'+''.join(f'<figure><a class="photo" data-index="{i}" href="{m["src"]}" aria-label="View {esc(m["title"])}">{self.image(m,m["alt"])}<span>View photograph ↗</span></a><figcaption>{esc(m["title"])}</figcaption></figure>' for i,m in enumerate(photos))+'</div>'
    def article(self,p,index):
        path=post_path(p);photos=self.media_for(p);cover=self.cover(p)
        terms=''.join(f'<a href="/blog/{"category" if t["taxonomy"]=="category" else "tag"}/{t["slug"]}/">{esc(t["name"])}</a>' for t in p['terms'])
        refs=[]
        for link in p['links']:
            linked=next((x for x in self.posts if post_path(x)==urlsplit(link).path),None)
            if linked and linked['slug']!=p['slug'] and linked not in refs:refs.append(linked)
        if len(refs)<3:refs += [x for x in self.posts if x['slug']!=p['slug'] and x not in refs and set(x['categories'])&set(p['categories'])][:3-len(refs)]
        related='<section class="related"><p class="eyebrow">CONTINUE EXPLORING</p><div class="stories">'+''.join(self.card(x) for x in refs[:3])+'</div></section>'
        body=f'''<main id="main" class="article-page"><div class="article-heading"><a class="back-link" href="/blog/">← Back to the Journal</a><p class="eyebrow">FIELD NOTES / {esc(' · '.join(p['categories']).upper())}</p><h1>{esc(p['title'])}</h1><p class="byline">By <a href="/#about">Jeroen Derwort</a> · <time datetime="{p['date'][:10]}">{date(p['date'])}</time> · {len(photos)} photographs</p></div><div class="article-cover">{self.image(cover,p['title'],size='src',lazy=False,sizes='90vw')}</div><div class="article-copy">{''.join('<p>'+esc(text)+'</p>' for text in p['paragraphs'])}</div>{self.gallery(photos)}<div class="article-tags" aria-label="Article topics">{terms}</div>{related}</main>'''
        self.page(p['title'],excerpt(p),path,body,photos,cover['src'],p)
    def journal(self):
        total=math.ceil(len(self.posts)/12)
        data=[{'title':p['title'],'description':excerpt(p),'path':post_path(p),'category':p['categories'][0] if p['categories'] else 'Photography','categories':p['categories'],'tags':[t['name'] for t in p['terms'] if t['taxonomy']=='post_tag'],'date':date(p['date']),'iso':p['date'][:10],'image':self.cover(p)['thumb']} for p in self.posts]
        categories=sorted(set(c for p in self.posts for c in p['categories']))
        for number in range(1,total+1):
            path='/blog/' if number==1 else f'/blog/page/{number}/'
            nav='<nav class="pagination" aria-label="Journal pages">'+''.join(f'<a href="{"/blog/" if n==1 else f"/blog/page/{n}/"}" '+('aria-current="page"' if n==number else '')+f'>{n}</a>' for n in range(1,total+1))+'</nav>'
            tools='<form class="journal-tools" role="search" onsubmit="return false"><label for="journal-search">Search the Journal<input id="journal-search" type="search" placeholder="Try Slovenia, Zoetermeer, sunset…" autocomplete="off"></label><label for="journal-category">Category<select id="journal-category"><option value="">All categories</option>'+''.join(f'<option>{esc(c)}</option>' for c in categories)+'</select></label></form><p id="search-status" class="search-status" role="status">72 photo stories · Page '+str(number)+' of '+str(total)+'</p>'
            body='<main id="main" class="journal-page section"><div class="section-heading"><div><p class="eyebrow">THE JOURNAL / FIELD NOTES</p><h1>Behind <em>the frame</em></h1></div><p>Places explored. Light discovered.<br>Stories from 2015–2021.</p></div>'+tools+'<div class="stories" id="journal-results">'+''.join(self.card(p) for p in self.posts[(number-1)*12:number*12])+'</div>'+nav+f'<script type="application/json" id="journal-data">{json_script(data)}</script></main>'
            self.page('Photography Journal'+(f' — Page {number}' if number>1 else ''),'Explore 72 photo stories by Jeroen Derwort, from Dutch landscapes and architecture to travel and abandoned places.',path,body)
        # Preserve the old homepage pagination and author archive.
        for n in range(2,19):
            page=min(total,math.ceil(n/3));self.redirects[f'/page/{n}/']='/blog/' if page==1 else f'/blog/page/{page}/'
        self.redirects['/blog/author/admin/']='/#about'
    def archives(self):
        terms={(t['taxonomy'],t['slug']):t['name'] for p in self.posts for t in p['terms']}
        for (taxonomy,slug),name in sorted(terms.items()):
            members=[p for p in self.posts if any(t['slug']==slug and t['taxonomy']==taxonomy for t in p['terms'])]
            path=f'/blog/{"category" if taxonomy=="category" else "tag"}/{slug}/'
            body=f'<main id="main" class="journal-page section"><a class="back-link" href="/blog/">← All photo stories</a><div class="section-heading"><div><p class="eyebrow">THE JOURNAL / {"CATEGORY" if taxonomy=="category" else "TOPIC"}</p><h1>{esc(name)}</h1></div><p>{len(members)} photo {"story" if len(members)==1 else "stories"}</p></div><div class="stories">'+''.join(self.card(p) for p in members)+'</div></main>'
            self.page(name+' photography',f'Explore {name} photography and personal photo stories by Jeroen Derwort.',path,body)
    def portfolios(self):
        summaries={'windmills':('Dutch windmills','Windmills, waterways and open skies. A collection of Dutch landscapes from Kinderdijk, the Zaanse Schans and beyond.'),'zoetermeer':('Zoetermeer','Finding something worth a second look close to home: lakes, neighbourhoods and architecture in and around Zoetermeer.'),'dubai':('Dubai','From waterfront reflections to colourful beachside details. Photographs collected during visits to Dubai.')}
        for slug,items in self.portfolio.items():
            photos=[];seen=set()
            for ref in items:
                key=normalized(ref['src'])
                if key in seen:continue
                seen.add(key);m=dict(self.media[key]);title=ref.get('alt') or ref.get('title') or m['caption']
                title=re.split(r'\s+(?:ILCE|SLT)\b|\|',title)[0].strip()
                if re.match(r'^DSC\d+',title,re.I):title=summaries[slug][0]
                photos.append(dict(m,title=title,alt=title+' — '+summaries[slug][0],detail='Photograph by Jeroen Derwort'))
            title,description=summaries[slug];path=f'/blog/portfolio-items/{slug}/'
            body=f'<main id="main" class="portfolio-page section"><a class="back-link" href="/portfolio/">← All collections</a><div class="section-heading"><div><p class="eyebrow">THE PORTFOLIO / {len(photos):02d} PHOTOGRAPHS</p><h1>{esc(title)}</h1></div><p>{esc(description)}</p></div>{self.gallery(photos)}</main>'
            self.page(title+' photography',description,path,body,photos,photos[0]['src'])
        cards=''
        for slug,(title,description) in summaries.items():
            ref=self.portfolio[slug][0];m=self.media[normalized(ref['src'])]
            cards+=f'<article><a class="story-image" href="/blog/portfolio-items/{slug}/">{self.image(m,title)}</a><h2><a href="/blog/portfolio-items/{slug}/">{title} ↗</a></h2><p>{description}</p></article>'
        body='<main id="main" class="portfolio-page section"><div class="section-heading"><div><p class="eyebrow">PHOTOGRAPHS / COLLECTIONS</p><h1>A sense <em>of place</em></h1></div><a class="text-link" href="/#photographs">View selected photographs ↗</a></div><div class="stories collection-cards">'+cards+'</div></main>'
        self.page('Photography collections','Explore Jeroen Derwort’s photography collections: Dutch windmills, Zoetermeer and Dubai.','/portfolio/',body)
        # Keep the original URL discoverable from the approved homepage.
    def extra(self):
        self.redirects.update({'/home/':'/','/about-me/':'/#about'})
        # A removed contact page should return 404, not redirect visitors to an unrelated article.
        for source,destination in self.redirects.items():
            self.write(source,f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={destination}"><link rel="canonical" href="{ORIGIN+destination}"><title>Page moved — Derwort Photo</title></head><body><p>This page has moved. <a href="{destination}">Continue to Derwort Photo</a>.</p></body></html>',sitemap=False)
        self.write('/404.html','<!doctype html><html lang="en"><head>'+self.head('Page not found','This page is no longer available. Explore the photography and Journal at Derwort Photo.','/')+'<meta name="robots" content="noindex"></head><body>'+self.header()+'<main id="main" class="not-found section"><p class="eyebrow">404 / A DIFFERENT PATH</p><h1>This frame is missing.</h1><p>The page may have moved or is no longer available.</p><a class="text-link" href="/">Explore the photographs ↗</a><a class="text-link" href="/blog/">Visit the Journal ↗</a></main>'+self.footer()+'</body></html>',sitemap=False)
        (self.out/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n')
        sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml(ORIGIN+p)+'</loc></url>' for p in self.urls)+'</urlset>'
        (self.out/'sitemap.xml').write_text(sitemap)
        feed='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Derwort Photo Journal</title><link>'+ORIGIN+'/blog/</link><description>Landscape, nature and travel photography by Jeroen Derwort.</description><language>en</language>'
        for p in self.posts:
            from email.utils import format_datetime
            from zoneinfo import ZoneInfo
            dt=datetime.fromisoformat(p['date']).replace(tzinfo=ZoneInfo('Europe/Amsterdam'));pub=format_datetime(dt)
            feed+=f'<item><title>{xml(p["title"])}</title><link>{ORIGIN+post_path(p)}</link><guid isPermaLink="true">{ORIGIN+post_path(p)}</guid><pubDate>{pub}</pubDate><description>{xml(excerpt(p))}</description></item>'
        (self.out/'feed.xml').write_text(feed+'</channel></rss>')
        redirect_lines=[f'{s} {d} 301' for s,d in self.redirects.items()]+['/feed/ /feed.xml 301','/blog/feed/ /feed.xml 301']
        # Preserve old shared image URLs on hosts that support redirects.
        redirect_lines += [f'{old} {m["src"]} 301' for old,m in self.media.items()]
        (self.out/'_redirects').write_text('\n'.join(redirect_lines)+'\n')
        (self.out/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/assets/*\n  Cache-Control: public, max-age=604800\n')
        (self.out/'.nojekyll').touch()
        # Apache rules cover real HTTP redirects, feeds and the removed contact page.
        apache='Options -Indexes\nErrorDocument 404 /404.html\nRewriteEngine On\n'
        for old,new in self.redirects.items():apache+=f'RewriteRule ^{re.escape(old.lstrip("/"))}$ {new.replace("#","\\#")} [R=301,L,NE]\n'
        for old,m in self.media.items():apache+=f'RewriteRule ^{re.escape(old.lstrip(chr(47)))}$ {m["src"]} [R=301,L]\n'
        apache+='RewriteRule ^(?:blog/)?feed/?$ /feed.xml [R=301,L]\n'
        (self.out/'.htaccess').write_text(apache)
    def build(self):
        self.out.mkdir(parents=True,exist_ok=True);shutil.copytree(ROOT/'public',self.out,dirs_exist_ok=True)
        self.home()
        for i,p in enumerate(self.posts):self.article(p,i)
        self.journal();self.archives();self.portfolios();self.extra()
        # Add an unobtrusive route to the migrated legacy portfolio collections.
        home=self.out/'index.html';s=home.read_text();needle='</div>\n</section>\n<section class="journal'
        s=s.replace(needle,'</div><a class="text-link collection-link" href="'+self.base+'/portfolio/">Explore the portfolio collections ↗</a>\n</section>\n<section class="journal',1);home.write_text(s)
        # Font URLs must also work under GitHub Pages project paths.
        if self.base:
            p=self.out/'style.css';p.write_text(p.read_text().replace('url(/assets/','url('+self.base+'/assets/'))
        print(f'Built {len(self.posts)} posts, {len(self.portfolio)} portfolios, {len(self.media)} photographs and {len(self.urls)} indexable pages in {self.out}')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='dist');parser.add_argument('--base-path',default='');args=parser.parse_args()
    out=(ROOT/args.out).resolve()
    if out==ROOT or ROOT in out.parents and out in [ROOT/'public',ROOT/'content',ROOT/'scripts',ROOT/'templates']:raise SystemExit('Choose a dedicated output directory')
    Builder(out,args.base_path).build()
if __name__=='__main__':main()
