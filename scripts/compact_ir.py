#!/usr/bin/env python3
"""Lossless transport format for model-produced flowchart JSON IR.

The compact form only reduces generated transport tokens; the canonical IR
format and validator remain unchanged. Reconstruction is exact in content.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

VERSION='flowchart-compact-v1'

def pack(ir:dict)->dict:
    refs=[];lookup={}
    def pidx(obj):
        key=json.dumps(obj,sort_keys=True,ensure_ascii=False)
        if key not in lookup:lookup[key]=len(refs);refs.append(obj)
        return lookup[key]
    functions=[]
    for fn in ir['functions']:
        nodes=[]
        for n in fn['nodes']:
            core=[n['id'],n['kind'],n['title'],[pidx(p) for p in n['params']],n['impact'],n['source_lines']]
            extra={k:v for k,v in n.items() if k not in ('id','kind','title','params','impact','source_lines')}
            nodes.append(core+([extra] if extra else []))
        extra_fn={k:v for k,v in fn.items() if k not in ('id','name','purpose','file','nodes')}
        functions.append([fn['id'],fn['name'],fn['purpose'],fn['file'],nodes]+([extra_fn] if extra_fn else []))
    edges=[]
    for e in ir['edges']:
        ex={k:v for k,v in e.items() if k not in ('from','to','label')}
        edges.append([e['from'],e['to'],e['label']]+([ex] if ex else []))
    extra={k:v for k,v in ir.items() if k not in ('title','source','functions','edges')}
    packed={'format':VERSION,'title':ir['title'],'source':ir['source'],'parameters':refs,'f':functions,'e':edges}
    if extra:packed['extra']=extra
    return packed

def unpack(p:dict)->dict:
    if p.get('format')!=VERSION:raise ValueError('unsupported compact format')
    functions=[]
    for f in p['f']:
        nodes=[]
        for n in f[4]:
            node={'id':n[0],'kind':n[1],'title':n[2],'params':[p['parameters'][i] for i in n[3]],'impact':n[4],'source_lines':n[5]}
            if len(n)>6:node.update(n[6])
            nodes.append(node)
        fn={'id':f[0],'name':f[1],'purpose':f[2],'file':f[3],'nodes':nodes}
        if len(f)>5:fn.update(f[5])
        functions.append(fn)
    edges=[]
    for e in p['e']:
        d={'from':e[0],'to':e[1],'label':e[2]}
        if len(e)>3:d.update(e[3])
        edges.append(d)
    res={'title':p['title'],'source':p['source'],'functions':functions,'edges':edges}
    res.update(p.get('extra',{}));return res

def main():
    p=argparse.ArgumentParser(description='Pack/unpack compact flowchart IR for reduced model output')
    p.add_argument('action',choices=['pack','unpack']);p.add_argument('src',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();data=json.loads(a.src.read_text(encoding='utf-8'))
    result=pack(data) if a.action=='pack' else unpack(data)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(a.out)
if __name__=='__main__':main()
