#!/usr/bin/env python3
"""Source indexer: AST-based Python function slicing without semantic invention.

Only direct, syntactically resolved local calls are traversed. No inference about
reflection, dynamic dispatch, imports, or external calls. Source ranges retain
original line numbers to preserve provenance; calls across files need separate
manual review or another verified index.
"""
from __future__ import annotations
import argparse
import ast
import json
import hashlib
from pathlib import Path

def select_functions(source:str,entries:list[str],depth:int=1)->dict:
    tree=ast.parse(source)
    fns={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    index={}
    for name,fn in fns.items():
        calls=set()
        for node in ast.walk(fn):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in fns:
                calls.add(node.func.id)
        index[name]={'start':fn.lineno,'end':fn.end_lineno,'calls':sorted(calls)}
    missing=[x for x in entries if x not in fns]
    if missing:raise ValueError('functions not present: '+', '.join(missing))
    levels={x:0 for x in entries}
    todo=list(entries)
    while todo:
        fn=todo.pop(0)
        if levels[fn]>=depth:continue
        for c in index[fn]['calls']:
            if c not in levels or levels[c]>levels[fn]+1:
                levels[c]=levels[fn]+1;todo.append(c)
    lines=source.splitlines()
    items=[]
    for fn in sorted(levels,key=lambda x:index[x]['start']):
        start,end=index[fn]['start'],index[fn]['end']
        items.append({'name':fn,'depth':levels[fn],'start':start,'end':end,
                      'calls':index[fn]['calls'], 'text':'\n'.join(f'{n:04d} {lines[n-1]}' for n in range(start,end+1))})
    return {'total_functions':len(fns),'selected_functions':len(items),'unfollowed_local_calls':sorted(set(c for v in items for c in v['calls'] if c not in levels)),'functions':items}

def main():
    p=argparse.ArgumentParser(description='Pin source ranges for focused LLM context (Python only)')
    p.add_argument('path',type=Path);p.add_argument('--entry',action='append',required=True)
    p.add_argument('--depth',type=int,default=1);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.depth<0:p.error('depth must be nonnegative')
    content=a.path.read_text(encoding='utf-8');index=select_functions(content,a.entry,a.depth)
    index['sha256']=hashlib.sha256(content.encode()).hexdigest();index['source_file']=str(a.path)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'functions':index['selected_functions'],'unfollowed_calls':index['unfollowed_local_calls'],'output':str(a.out)},ensure_ascii=False))
if __name__=='__main__':main()
