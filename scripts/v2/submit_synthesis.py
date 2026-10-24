#!/usr/bin/env python3
"""Compile one reviewed private Markdown commit. Invoked by an approved host workflow."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess


def changed_synthesis(private,before,after):
    if any(not re.fullmatch(r'[0-9a-f]{40}',v) for v in (before,after)):
        raise ValueError('Exact input commit SHAs required')
    paths=subprocess.check_output(['git','diff','--name-only',before,after,'--','sources/synthesis/'],cwd=private,text=True).splitlines()
    if len(paths)!=1 or not re.fullmatch(r'sources/synthesis/\d{4}-\d{2}-\d{2}-(morning|midday|evening)\.md',paths[0]):
        raise ValueError('Submit exactly one edition Markdown file')
    original=Path(private)/paths[0];path=original.resolve()
    if original.is_symlink() or not path.is_relative_to(Path(private).resolve()) or not path.is_file():
        raise ValueError('Unsafe synthesis path')
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True)
    p.add_argument('--before',required=True);p.add_argument('--after',required=True);p.add_argument('--github-output',type=Path)
    args=p.parse_args();path=changed_synthesis(args.private_root,args.before,args.after)
    edition=path.stem;pack=args.private_root/'research/runs'/edition/'research_pack.json'
    if path.stat().st_size>60000:
        raise ValueError('Oversized synthesis')
    spec=importlib.util.spec_from_file_location('synthesis_compose',Path(__file__).with_name('compose.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    value.compose_edition(path,root=args.root,research_pack=pack)
    if args.github_output:
        with args.github_output.open('a',encoding='utf-8') as stream:
            stream.write('edition_id='+edition+'\n')


if __name__=='__main__':main()
