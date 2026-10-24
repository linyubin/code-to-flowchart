#!/usr/bin/env python3
"""Optional Graphviz-only preview; does NOT validate Mermaid rendering."""
import argparse
import html
import json
import subprocess
from urllib.parse import quote
from pathlib import Path


def q(x):
    return '"' + str(x).replace('\\','\\\\').replace('"','\\"') + '"'

def label(s):
    return html.escape(str(s), quote=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('ir',type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    m=json.loads(a.ir.read_text(encoding='utf-8'))
    s=['digraph G {','graph [fontname="Noto Sans CJK SC",rankdir=TB,compound=true,newrank=true,splines=polyline,pad=0.3,nodesep=0.35,ranksep=0.65,bgcolor="#FAFAF8",size="20,40",ratio=compress];','node [fontname="Noto Sans CJK SC",fontsize=10,style="filled,rounded",color="#aab3bb",fillcolor="white",penwidth=1.2,margin="0.14,0.1"];','edge [fontname="Noto Sans CJK SC",fontsize=9,arrowsize=0.55,color="#657589"];']
    for i,f in enumerate(m['functions']):
        s.extend([f'subgraph cluster_{f["id"]} {{',f'label={q(f["name"]+"  |  "+f["purpose"])};', 'fontname="Noto Sans CJK SC";fontsize=13;fontcolor="#203a55";style="rounded,filled";color="#b9ccd8";fillcolor='+q(['#f0f7fc','#f6f7fb','#f1f8f4','#fff8f0','#f9f3ff'][i%5])+';penwidth=1.8;'])
        for n in f['nodes']:
            params=', '.join(p['name'] for p in n['params']) or '—'
            if len(params)>68:params=params[:65]+'…'
            effect=n['impact']
            if len(effect)>60:effect=effect[:57]+'…'
            v=f'<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="1" CELLPADDING="2"><TR><TD><B>{label(n["title"])}</B></TD></TR><TR><TD><FONT COLOR="#55718b" POINT-SIZE="9">P: {label(params)}</FONT></TD></TR><TR><TD><FONT COLOR="#305949" POINT-SIZE="9">Δ: {label(effect)}</FONT></TD></TR></TABLE>'
            shape='diamond' if n['kind']=='decision' else ('oval' if n['kind'] in {'start','terminal','error'} else 'box')
            bg='#fff0ee' if n['kind']=='error' else ('#fff9e9' if n['kind']=='decision' else 'white')
            src=f["file"]+':'+str(n['source_lines'][0]);
            repo=m.get('source',{}).get('repository','')
            url=(f'https://github.com/{quote(repo,safe="/")}/blob/{quote(m["source"]["revision"],safe="")}/{quote(f["file"],safe="/")}#L{n["source_lines"][0]}' if repo else '')
            s.append(f'{q(n["id"])} [label=<{v}>,shape={shape},fillcolor={q(bg)},tooltip={q(src)},URL={q(url)},target="_blank"];')
        s.append('}')
    for e in m['edges']:
        kw=f'[label={q(e["label"])}'
        if e.get('kind')=='fallback':kw+=',style=dashed,color="#b86c57"'
        s.append(f'{q(e["from"])} -> {q(e["to"])} {kw}];')
    s.append('}')
    out=a.out or a.ir.with_suffix('.svg')
    result=subprocess.run(['dot','-Tsvg','-o',str(out)],input='\n'.join(s),text=True,capture_output=True)
    if result.returncode:raise SystemExit(result.stderr)
    print('Rendered Graphviz preview:',out)

if __name__=='__main__':main()
