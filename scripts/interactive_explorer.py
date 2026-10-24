#!/usr/bin/env python3
"""Render a reviewed, function-scoped view specification to an offline HTML explorer.

Input view spec: {source: {...}, views: [{key,title,purpose,nodes,edges,file,
family:overview|function, stages:[{title,items:[node_id|[node_id,...]]}]}],
tracks: [{key,label,summary,steps:[{view,node,note}]}]}.
Requires Graphviz only when building; the generated HTML has no runtime dependencies.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
COLORS={"start":"#E7F3F9","action":"#FFFFFF","call":"#EAF3FF","decision":"#FFF2DB","terminal":"#E5F6ED","error":"#FFEBE9"}
STROKES={"start":"#6495AD","action":"#CBD7E4","call":"#678DB9","decision":"#D7A04B","terminal":"#5EA985","error":"#C67F78"}
def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
def h(value):return html.escape(str(value),quote=True)
def shorten(s,limit=44):
  s=str(s).strip();return s if len(s)<=limit else s[:limit-1]+'…'

def validate_views(spec):
  if not spec.get('source') or not spec.get('views'):raise ValueError('source and views required')
  views=spec['views'];ids=[v['key'] for v in views]
  if len(ids)!=len(set(ids)) or ids[0]!='overview':raise ValueError('first view must be uniquely named overview')
  for v in views:
    required=('key','title','name','purpose','nodes','edges','file','family')
    if any(k not in v for k in required):raise ValueError('missing required view fields')
    known={n['id'] for n in v['nodes']}
    if len(known)!=len(v['nodes']):raise ValueError('duplicate node ids')
    if v['family']=='overview' and len(v.get('stages',[]))!=3:raise ValueError('overview requires exactly three stages')
    for e in v['edges']:
      if e['from'] not in known or e['to'] not in known:raise ValueError('edge outside view: '+str(e))
    for n in v['nodes']:
      if n.get('kind') not in COLORS or not n.get('title') or not n.get('impact'):raise ValueError('invalid node: '+str(n))
      if n.get('jump') and n['jump'] not in ids:raise ValueError('unknown jump view')
    for group in v.get('stages',[]):
      for it in group.get('items',[]):
        for nid in it if isinstance(it,list) else [it]:
          if nid not in known:raise ValueError('unknown overview stage node '+nid)
  for t in spec.get('tracks',[]):
    for step in t.get('steps',[]):
      target=next((v for v in views if v['key']==step['view']),None)
      if not target or step['node'] not in {n['id'] for n in target['nodes']}:
        raise ValueError('unknown trace step '+str(step))
  return True
def node_dot(n):
    kind=n['kind']; bg=COLORS.get(kind,'#fff'); color=STROKES.get(kind,'#ccc')
    p=', '.join(p['name'] for p in n.get('params',[])) or '—'
    impact=n.get('impact','—')
    # Parameter and impact annotations remain on every visual node. Full details appear in side panel.
    label=f'< <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="1" CELLPADDING="2">' \
          f'<TR><TD><FONT POINT-SIZE="11"><B>{h(shorten(n["title"],32))}</B></FONT></TD></TR>' \
          f'<TR><TD><FONT COLOR="#50708A" POINT-SIZE="9">P: {h(shorten(p,40))}</FONT></TD></TR>' \
          f'<TR><TD><FONT COLOR="#306B5B" POINT-SIZE="9">Δ: {h(shorten(impact,42))}</FONT></TD></TR>' \
          f'</TABLE> >'
    shape='diamond' if kind=='decision' else ('ellipse' if kind in ('start','terminal','error') else 'box')
    return f'{quote(n["id"])} [id={quote("node-"+n["id"])},shape={shape},fillcolor={quote(bg)},color={quote(color)},label={label}];'

def dot_svg(view):
    if not shutil.which('dot'): raise RuntimeError('Graphviz dot is needed to build the standalone viewer')
    lr=False # vertical layout keeps labels readable in the fixed-size viewport
    s=['digraph Flow {', 'graph [fontname="Noto Sans CJK SC", rankdir='+('LR' if lr else 'TB')+', bgcolor="transparent", nodesep=0.35, ranksep='+('0.72' if lr else '0.5')+', splines=polyline, pad=0.28, outputorder=edgesfirst];', 'node [fontname="Noto Sans CJK SC", style="rounded,filled", penwidth=1.45, margin="0.16,0.13"];', 'edge [fontname="Noto Sans CJK SC", fontsize=9, color="#8396A9", fontcolor="#60758A", penwidth=1.2, arrowsize=0.6];']
    s.append('subgraph cluster_function {')
    s.append('graph [id="function-scope", label='+quote('函数范围  '+view['name']+'  |  '+view['purpose'][:42]) +', labelloc=t, labeljust=l, fontname="Noto Sans CJK SC",fontsize=12,fontcolor="#51738D",style="rounded,filled",fillcolor="#F8FBFE",color="#C6DAE7",penwidth=1.5,margin=20];')
    for n in view['nodes']:s.append(node_dot(n))
    s.append('}')
    for e in view['edges']:
        color='#bf8472' if e.get('kind')=='fallback' else '#8396A9'
        s.append(f'{quote(e["from"])} -> {quote(e["to"])} [id={quote("edge-"+e["from"]+"-"+e["to"])},label={quote(shorten(e.get("label",""),12))},color={quote(color)}];')
    s.append('}')
    p=subprocess.run(['dot','-Tsvg'],input='\n'.join(s),text=True,capture_output=True)
    if p.returncode:raise RuntimeError('dot rendering failed: '+p.stderr[:1000])
    svg=re.search(r'<svg\b[\s\S]*?</svg>',p.stdout).group(0)
    svg=svg.replace('width="','data-intrinsic-width="',1).replace('height="','data-intrinsic-height="',1)
    # Make graph viewport controlled solely by the HTML pane.
    svg=svg.replace('<svg ', '<svg width="100%" height="100%" role="img" aria-label="交互流程图" ',1)
    return svg

def source_url(source,file,lines):
    repo=source.get('repository','')
    commit=source.get('revision','')
    return f'https://github.com/{repo}/blob/{commit}/{file}'+(f'#L{lines[0]}' if lines else '')

def render_html(views, source, tracks, tpl):
    svg={v['key']:dot_svg(v) for v in views}
    titles={v['key']:v['title'] for v in views}
    all_ids={n['id'] for v in views for n in v['nodes']}
    for t in tracks:
        for step in t['steps']:
            if step['node'] not in all_ids: raise ValueError(f'Unknown parameter trace node: {step}')
            if step['view'] not in titles: raise ValueError(f'Unknown parameter trace view: {step}')
    for v in views:
        for n in v['nodes']:
            n['source_url']=source_url(source,v['file'],n.get('source_lines',[]))
            n['function']=v['title']
    doc=Path(tpl).read_text(encoding='utf-8')
    json_safe=lambda v:json.dumps(v,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return doc.replace('__VIEWS_JSON__',json_safe(views)).replace('__SVG_JSON__',json_safe(svg)).replace('__TRACKS_JSON__',json_safe(tracks)).replace('__SOURCE_JSON__',json_safe(source))

def main():
  p=argparse.ArgumentParser(description=__doc__)
  p.add_argument('spec',type=Path,help='Reviewed view spec JSON')
  p.add_argument('--out',type=Path,required=True)
  args=p.parse_args()
  spec=json.loads(args.spec.read_text(encoding='utf-8'))
  validate_views(spec)
  html=render_html(spec['views'],spec['source'],spec.get('tracks',[]),Path(__file__).parent.parent/'templates'/'explorer.html')
  args.out.parent.mkdir(parents=True,exist_ok=True)
  args.out.write_text(html,encoding='utf-8')
  print(json.dumps({'output':str(args.out),'views':len(spec['views']),'bytes':len(html.encode('utf-8'))},ensure_ascii=False))
if __name__=='__main__':main()
