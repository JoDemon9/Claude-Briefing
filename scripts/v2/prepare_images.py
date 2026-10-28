#!/usr/bin/env python3
"""Cache editorially selected, licensed photographs. Never select stories or publish."""
import argparse
import io
import hashlib
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
    partial = edition.get('availability_policy') == 'partial-v1' and edition.get('date','') >= '2026-10-22' and edition.get('photo_policy') != 'real-photos-v1'
    count = 0
    for relative in edition['articles']:
        path = root/'content'/relative
        article = json.loads(path.read_text())
        im = article.get('image')
        if not im:
            if edition.get('photo_policy') == 'real-photos-v1':
                raise ValueError('Mandatory real photograph missing: ' + article['id'])
            continue
        local = Path(im['url'])
        if local.is_absolute() or '..' in local.parts or not im['url'].startswith('assets/editorial/'):
            raise ValueError('Unsafe editorial asset path')
        target = root/'docs'/local
        if im.get('source_review'):
            # Sealed source images are submitted with the candidate; never refetch
            # mutable publisher bytes during CI or pretend a missing asset passed.
            import importlib.util
            spec = importlib.util.spec_from_file_location('prepared_source_photos', Path(__file__).with_name('source_photos.py'))
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.validate_image(im, target.read_bytes())
        downloaded = False
        reuse=im.get('reuse_review')
        if reuse:
            source=Path(reuse['source_asset'])
            if source.is_absolute() or '..' in source.parts or not source.as_posix().startswith('assets/editorial/'):
                raise ValueError('Unsafe reused photo provenance')
            original=root/'docs'/source
            if not reuse.get('relevance_and_archive_date_checked') or hashlib.sha256(original.read_bytes()).hexdigest()!=reuse['sha256']:
                raise ValueError('Reused photo source no longer matches its review')
            if not target.exists() and not verify_only:
                # A reused photo is already optimized and reviewed byte-for-byte.
                # Downloading/re-encoding its remote original changes that identity.
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original.read_bytes())
        if not target.exists():
            if verify_only:
                raise ValueError('Missing image asset: '+str(local))
            try:
                url = im.get('download_url',im['original_url'])
                parsed = urlsplit(url)
                if parsed.scheme != 'https' or parsed.hostname not in HOSTS:
                    raise ValueError('Unapproved image origin')
                raw = None
                for attempt in range(2):
                    try:
                        request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})
                        with urllib.request.urlopen(request, timeout=20) as response:
                            if urlsplit(response.geturl()).hostname not in HOSTS:
                                raise ValueError('Unapproved image redirect')
                            if not response.headers.get_content_type().startswith('image/'):
                                raise ValueError('Image response is not an image')
                            raw = response.read(MAX_BYTES+1)
                        break
                    except (OSError, TimeoutError):
                        if attempt == 1:
                            raise
                        time.sleep(1)
                if not raw or len(raw) > MAX_BYTES:
                    raise ValueError('Image exceeds size limit or empty')
                with Image.open(io.BytesIO(raw)) as original:
                    original.load()
                    image = ImageOps.exif_transpose(original).convert('RGB')
                    image.thumbnail((1280,1280))
                    if min(image.size) < 200:
                        raise ValueError('Image resolution too small')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target, 'WEBP', quality=82, method=6)
                    downloaded = True
            except Exception as error:
                if partial:
                    article['image'] = None
                    article['image_unavailable_reason'] = 'Η ελεγμένη φωτογραφία δεν είναι προσωρινά διαθέσιμη.'
                    path.write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                    target.unlink(missing_ok=True)
                    continue
                raise ValueError('Reviewed photograph could not be prepared: '+str(local)) from error
        try:
            with Image.open(target) as img_check:
                if min(img_check.size) < 200:
                    raise ValueError('Editorial photograph is too small')
                img_check.verify()
        except Exception as error:
            raise ValueError('Invalid reviewed photograph: '+str(local)) from error
        if reuse and hashlib.sha256(target.read_bytes()).hexdigest()!=reuse['sha256']:
            raise ValueError('Reused photo bytes do not match their reviewed source')
        if target.stat().st_size > 1_000_000:
            raise ValueError('Optimized image is too large')
        count += 1
        print('Verified image:', local)
        if downloaded:
            time.sleep(3)
    if edition.get('image_review') and count == 0 and not partial:
        raise ValueError('No photographs found for reviewed edition')
    print(f'{count} local editorial images verified for {edition_id}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    prepare(args.root, args.edition, args.verify_only)
