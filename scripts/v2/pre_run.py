#!/usr/bin/env python3
"""Host-side entry point. Never invoked as a research fallback inside an AI task."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def scheduled_slot(at):
    local=at.astimezone(ZoneInfo('Europe/Athens'))
    return {7:'morning',13:'midday',19:'evening'}.get(local.hour) if 5<=local.minute<30 else None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True)
    p.add_argument('--wire-root',type=Path);p.add_argument('--slot',choices=('morning','midday','evening'))
    p.add_argument('--scheduled',action='store_true');p.add_argument('--github-output',type=Path)
    args=p.parse_args();now=datetime.now(timezone.utc);slot=scheduled_slot(now) if args.scheduled else args.slot
    if not slot:
        if args.scheduled:
            print('Outside pre-run window; no collection or AI invocation.');return
        p.error('--slot is required for a manual pre-run')
    spec=importlib.util.spec_from_file_location('preparer',Path(__file__).with_name('prepare_run.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    result=value.prepare(args.root,now.astimezone(ZoneInfo('Europe/Athens')).date().isoformat(),slot,now.isoformat(),args.private_root,args.wire_root)
    if args.github_output:
        with args.github_output.open('a',encoding='utf-8') as stream:
            stream.write('edition_id='+result['edition_id']+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
