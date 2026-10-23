"""Import WordPress photographs; original downloads stay in an external backup directory.
Requires Pillow only for this one-time import, never for building the website.
"""
import argparse, concurrent.futures, hashlib, html, json, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parents[1]
class Images(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and 'fusion-lightbox' in a.get('class','') and '/files/' in a.get('href',''):
            self.items.append({'src':a['href'],'alt':a.get('data-title',''),'title':a.get('data-caption','')})
        if tag=='img' and '/files/' in a.get('src',''):
            self.items.append({'src':a['src'],'alt':a.get('alt',''),'title':a.get('title','')})
def normalized(url):
    path=unquote(urlsplit(html.unescape(url)).path)
    return re.sub(r'-\d+x\d+(?=\.[^.]+$)','',path)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--backup-directory',default='/tmp/derwort-photo-originals');args=parser.parse_args()
    posts=json.loads((ROOT/'content/migration/source-posts.json').read_text())
    refs=[i for p in posts for i in p['images']]+[{'src':p['featured'],'alt':p['title']} for p in posts if p['featured']]
    portfolio=json.loads((ROOT/'content/migration/portfolio.json').read_text())
    for items in portfolio.values():refs+=items
    features={'zaanse-schans':'/files/2017/09/DSC04227-2.jpg','texel':'/files/2017/10/DSC05131.jpg','senhor-da-pedra':'/files/2018/08/DSC08758.jpg','night':'/files/2018/07/DSC00760-Edit-5.jpg','wonderful-light':'/files/2017/10/DSC05522.jpg'}
    refs += [{'src':'https://www.derwortphoto.com'+v,'alt':k} for k,v in features.items()]
    unique={}
    for ref in refs:
        key=normalized(ref['src'])
        if key not in unique or len(ref.get('alt',''))>len(unique[key].get('alt','')): unique[key]=ref
    target=ROOT/'public/assets/photos';target.mkdir(parents=True,exist_ok=True)
    backup=Path(args.backup_directory).expanduser();backup.mkdir(parents=True,exist_ok=True)
    manifest_path=ROOT/'content/migration/media.json'
    prior=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    def download(pair):
        key,ref=pair
        if key in prior and all((ROOT/'public'/prior[key][variant].lstrip('/')).exists() for variant in ['src','medium','thumb']):return key,prior[key]
        filename=re.sub(r'[^a-zA-Z0-9_-]','-',Path(key).stem).lower()+'-'+hashlib.sha256(key.encode()).hexdigest()[:8]
        original=backup/(filename+Path(key).suffix)
        if not original.exists():
            subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','3','--max-time','90','https://www.derwortphoto.com'+key,'-o',str(original)],check=True)
        with Image.open(original) as image:
            image=ImageOps.exif_transpose(image).convert('RGB'); w,h=image.size
            for size in [640,1200,2400]:
                thumb=image.copy();thumb.thumbnail((size,size),Image.Resampling.LANCZOS)
                thumb.save(target/(filename+f'-{size}.webp'),'WEBP',quality=85,method=4)
        caption=re.split(r'\s+(?:ILCE|SLT|DSC|SONY)\b|\|',html.unescape(ref.get('alt') or ref.get('title') or ''))[0].strip()
        if not caption or re.match(r'^DSC\d+',caption):caption=''
        return key,{'src':f'/assets/photos/{filename}-2400.webp','medium':f'/assets/photos/{filename}-1200.webp','thumb':f'/assets/photos/{filename}-640.webp','width':w,'height':h,'caption':caption,'original_url':'https://www.derwortphoto.com'+key}
    manifest={};errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures={executor.submit(download,item):item[0] for item in unique.items()}
        for future in concurrent.futures.as_completed(futures):
            try:
                k,v=future.result();manifest[k]=v
                if len(manifest)%25==0:print(f'{len(manifest)}/{len(unique)} photographs imported',flush=True)
            except Exception as exc:errors.append({'path':futures[future],'error':str(exc)});print('FAILED',futures[future],str(exc),flush=True)
    manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'content/migration/portfolio.json').write_text(json.dumps(portfolio,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'content/migration/features.json').write_text(json.dumps(features,indent=2)+'\n')
    (ROOT/'content/migration/media-errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    print(f'Finished: {len(manifest)} photographs; {len(errors)} errors',flush=True)
    if errors:sys.exit(1)
if __name__=='__main__':main()
