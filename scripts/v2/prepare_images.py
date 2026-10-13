#!/usr/bin/env python3
"""Cache editorially selected, licensed photographs. Never select stories or publish."""
import argparse
import io
import json
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
HOSTS = {'upload.wikimedia.org', 'thumb.wikimedia.org'}
MAX_BYTES = 60_000_000


def prepare(root, edition_id, verify_only=False):
    root = Path(root)
    edition = json.loads((root/'content/editions'/f'{edition_id}.json').read_text())
    count = 0
    for relative in edition['articles']:
        path = root/'content'/relative
        article = json.loads(path.read_text())
        im = article.get('image')
        if not im:
            continue
        local = Path(im['url'])
        if local.is_absolute() or '..' in local.parts or not im['url'].startswith('assets/editorial/'):
            raise ValueError('Unsafe editorial asset path')
        target = root/'docs'/local
        if not target.exists():
            if verify_only:
                raise ValueError('Missing image asset: '+str(local))
            url = im['original_url']
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or parsed.hostname not in HOSTS:
                raise ValueError('Unapproved image host; review the publisher before extending HOSTS')
            raw = None
            for attempt in range(3):
                try:
                    request = urllib.request.Request(url, headers={'User-Agent':'OracleBriefing/1.0 (licensed editorial image cache)'})
                    with urllib.request.urlopen(request, timeout=60) as response:
                        if urlsplit(response.geturl()).hostname not in HOSTS:
                            raise ValueError('Unexpected image redirect')
                        if not response.headers.get_content_type().startswith('image/'):
                            raise ValueError('Image response is not an image')
                        raw = response.read(MAX_BYTES+1)
                    break
                except (OSError, TimeoutError):
                    if attempt == 2:
                        raise
                    time.sleep(2+attempt*2)
            if len(raw) > MAX_BYTES:
                raise ValueError('Image exceeds size limit')
            with Image.open(io.BytesIO(raw)) as original:
                original.load()
                image = ImageOps.exif_transpose(original).convert('RGB')
                image.thumbnail((1280,1280))
                if min(image.size) < 200:
                    raise ValueError('Image resolution too small')
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target, 'WEBP', quality=82, method=6)
        with Image.open(target) as image:
            image.verify()
        if target.stat().st_size > 1_000_000:
            raise ValueError('Optimized image is too large')
        count += 1
        print('Verified image:', local)
    if edition.get('image_review') and count == 0:
        raise ValueError('No photographs found for reviewed edition')
    print(f'{count} local editorial images verified for {edition_id}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    prepare(args.root, args.edition, args.verify_only)
