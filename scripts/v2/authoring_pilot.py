"""Replay equivalent saved JSON/Markdown inputs; report bytes, never inferred tokens."""
import argparse
import importlib.util
import json
from pathlib import Path


def module(name):
    spec=importlib.util.spec_from_file_location('pilot_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def compare(payload, root):
    authoring=module('markdown_input');compiler=module('compose')
    text=authoring.export(payload)
    left=compiler.compile_payload(payload,root)
    right=compiler.compile_payload(authoring.parse(text,root),root)
    if left != right:
        raise ValueError('Markdown replay changed canonical content')
    raw=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
    compact=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    return {'edition_id':payload['edition_id'],'canonical_parity':True,'json_bytes':len(raw),'compact_json_bytes':len(compact),'markdown_bytes':len(text.encode('utf-8')),
            'actual_input_tokens':None,'actual_output_tokens':None,'account_quota_saving':None,
            'scope':'Stored-input replay only. Bytes are not tokens; no fresh research, model run or live task installation is implied.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--input',type=Path,action='append',required=True)
    args=parser.parse_args()
    print(json.dumps([compare(json.loads(path.read_text(encoding='utf-8')),args.root) for path in args.input],ensure_ascii=False,indent=2))
