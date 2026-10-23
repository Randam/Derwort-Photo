#!/usr/bin/env python3
"""Export the migration redirects for Cloudflare's account-level Bulk Redirects API."""
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
def main():
    aliases={}
    for line in (ROOT/'dist/_redirects').read_text().splitlines():
        source,target,status=line.split()
        aliases[source]=target
    media=json.loads((ROOT/'content/migration/media.json').read_text())
    posts=json.loads((ROOT/'content/migration/source-posts.json').read_text())
    for post in posts:
        for image in post['images']:
            path=unquote(urlsplit(image['src']).path)
            if path not in aliases:
                import re
                key=re.sub(r'-\d+x\d+(?=\.[^.]+$)','',path)
                if key in media:aliases[path]=media[key]['src']
    items=[{'redirect':{'source_url':host+path,'target_url':'https://www.derwortphoto.com'+target,'status_code':301,'preserve_query_string':True,'include_subdomains':False,'subpath_matching':False,'preserve_path_suffix':False}} for host in ['www.derwortphoto.com','derwortphoto.com'] for path,target in sorted(aliases.items())]
    dest=ROOT/'dist/cloudflare-redirects.json';dest.write_text(json.dumps(items,indent=2)+'\n')
    print(f'Exported {len(items)} Cloudflare redirects covering {len(aliases)} old paths on both hostnames')
if __name__=='__main__':main()
