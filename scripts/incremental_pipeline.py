#!/usr/bin/env python3
"""Idempotent local render pipeline with versioned source fingerprint checks.

Cache only skips deterministic output generation. An agent may skip LLM
analysis using an IR only when independently verified provenance matches.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from flowchart_ir import load_ir, render_mermaid, render_report, validate_ir
from token_usage import append_event
from interactive_explorer import render_html, validate_views

SCHEMA=1

def fingerprint(paths: list[Path], revision: str, request: str='')->str:
    h=hashlib.sha256()
    h.update(json.dumps([SCHEMA,revision,request],ensure_ascii=False).encode())
    for path in paths:
        h.update(str(path.resolve()).encode());h.update(path.read_bytes())
    return h.hexdigest()

def build(ir:Path,output_dir:Path,log:Path|None=None,source_files:list[Path]|None=None,request:str='',force:bool=False,viewer_spec:Path|None=None)->dict:
    data=load_ir(ir)
    errors=validate_ir(data)
    if errors:raise ValueError('; '.join(errors))
    output_dir.mkdir(parents=True,exist_ok=True)
    mmd=output_dir/(ir.stem+'.mmd');markdown=output_dir/(ir.stem+'.md')
    provenance=output_dir/(ir.stem+'.cache.json')
    sources=source_files or []
    # Require full revision match and content hashes to mark any user-provided source cache reusable.
    template=Path(__file__).resolve().parent.parent/'templates'/'explorer.html'
    viewer_deps=[viewer_spec, Path(__file__).with_name('interactive_explorer.py'),template] if viewer_spec else []
    sig=fingerprint([ir,Path(__file__),Path(__file__).with_name('flowchart_ir.py')]+sources+viewer_deps,data['source']['revision'],request)
    last=json.loads(provenance.read_text(encoding='utf-8')) if provenance.exists() else {}
    current_ir_sha=hashlib.sha256(ir.read_bytes()).hexdigest()
    current_sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    previous_sources={v['name']:v['sha256'] for v in last.get('sources',[])}
    # Source changed without a new analysis IR: stop rather than redrawing stale logic.
    if previous_sources and previous_sources!=current_sources and last.get('ir_sha256')==current_ir_sha:
        raise ValueError('source content changed but IR is unchanged: re-analyze code and regenerate/review the IR before rendering')
    viewer_out=output_dir/(viewer_spec.stem+'.html') if viewer_spec else None
    hit=not force and last.get('fingerprint')==sig and mmd.exists() and markdown.exists() and (not viewer_out or viewer_out.exists())
    if not hit:
        output=render_mermaid(data)
        mmd.write_text(output,encoding='utf-8')
        markdown.write_text(render_report(data,output),encoding='utf-8')
        if viewer_spec:
            spec=json.loads(viewer_spec.read_text(encoding='utf-8'))
            validate_views(spec)
            if spec['source']['revision']!=data['source']['revision']:
                raise ValueError('viewer spec source revision does not match canonical IR')
            viewer_out.write_text(render_html(spec['views'],spec['source'],spec.get('tracks',[]),template),encoding='utf-8')
        provenance.write_text(json.dumps({'schema_version':SCHEMA,'fingerprint':sig,'source_revision':data['source']['revision'], 'ir_sha256':current_ir_sha,
                                          'sources':[{'name':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if log:append_event(log,{'stage':'render','run_id':request or 'local','measurement':'cache_hit' if hit else 'local','fingerprint':sig})
    return {'cache_hit':hit,'output':str(mmd),'markdown':str(markdown),'viewer':str(viewer_out) if viewer_out else None,'revision':data['source']['revision'],'functions':len(data['functions']),
            'nodes':sum(len(f['nodes']) for f in data['functions'])}

def main():
    p=argparse.ArgumentParser(description='Deterministic, validated and cached flowchart rendering')
    p.add_argument('ir',type=Path);p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--source',action='append',type=Path,default=[])
    p.add_argument('--request',default='');p.add_argument('--usage-log',type=Path);p.add_argument('--viewer-spec',type=Path);p.add_argument('--force',action='store_true')
    a=p.parse_args()
    print(json.dumps(build(a.ir,a.out_dir,a.usage_log,a.source,a.request,a.force,a.viewer_spec),ensure_ascii=False))
if __name__=='__main__':main()
