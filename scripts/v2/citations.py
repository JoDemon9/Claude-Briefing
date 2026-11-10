"""Authoring aliases are validated privately and never printed as public prose."""
import re

GROUP=re.compile(r'\[\s*([a-z][a-z0-9-]*(?:\s*[,;]\s*[a-z][a-z0-9-]*)*)\s*\]')
PUBLIC=re.compile(r'\[\s*[es]\d+(?:\s*[,;]\s*[es]\d+)*\s*\]')


def resolve(value, sources):
    if isinstance(value,list):return [resolve(v,sources) for v in value]
    if isinstance(value,dict):return {k:resolve(v,sources) for k,v in value.items()}
    if not isinstance(value,str):return value
    def replace(match):
        aliases=re.split(r'\s*[,;]\s*',match[1])
        if not set(aliases)<=set(sources):raise ValueError('Unresolved source reference: '+match[0])
        return ''
    result=GROUP.sub(replace,value)
    if re.search(r'\[\s*[es]\d+\b',result):raise ValueError('Malformed source reference')
    return result.strip()


def public_text(value):
    """Legacy render compatibility; source snapshots and fingerprints stay intact."""
    return PUBLIC.sub('',value)
