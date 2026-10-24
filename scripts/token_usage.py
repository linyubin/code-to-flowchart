#!/usr/bin/env python3
"""Token usage ledger. No secrets or prompt text written into metrics.

Exact counts require usage data from the model API/agent. Without usage, use
an explicitly labeled, deterministic character heuristic (NOT billed tokens).
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

STAGES = ('load_skill', 'read_source', 'reason_logic', 'write_ir', 'render', 'validate')

def rough_tokens(text: str) -> int:
    """Approximation only; deliberately does not claim model tokenizer fidelity.

    CJK chars are costed at 1.25 and ASCII text at 1 / 3.1 chars (mixed
    prose/code). Returns integer, with a minimum of one for nonempty inputs.
    """
    if not text: return 0
    cjk = sum(1 for c in text if '\u3400' <= c <= '\u9fff')
    return max(1, round(cjk * 1.25 + (len(text) - cjk) / 3.1))

def file_measure(paths: list[Path]) -> dict:
    n, digests, chars = 0, [], 0
    for path in paths:
        data = path.read_bytes()
        content = data.decode('utf-8')
        n += rough_tokens(content); chars += len(content)
        digests.append({'name': path.name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    return {'estimated_tokens': n, 'characters': chars, 'sha256': hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest(), 'files': [{'name':v['name'],'bytes':v['bytes']} for v in digests]}

def parse_usage(data: dict, provider: str) -> dict:
    """Normalize provider usage, do not double-count reasoning tokens.

    OpenAI output_tokens already includes reasoning_tokens, hence reasoning is
    a subset and is never added to total. Anthropic cache_read_* can be
    separate from input_tokens; normalize total as input + cache_read + cache_creation.
    """
    u = data.get('usage', data)
    if provider == 'openai':
        input_tokens = u.get('input_tokens', u.get('prompt_tokens'))
        output_tokens = u.get('output_tokens', u.get('completion_tokens'))
        details_i = u.get('input_tokens_details') or u.get('prompt_tokens_details') or {}
        details_o = u.get('output_tokens_details') or u.get('completion_tokens_details') or {}
        cached = details_i.get('cached_tokens', 0) or 0
        reasoning = details_o.get('reasoning_tokens', 0) or 0
        total = u.get('total_tokens', None)
        if total is None and input_tokens is not None and output_tokens is not None:
            total = input_tokens + output_tokens
    elif provider == 'anthropic':
        regular = u.get('input_tokens', None)
        cache_read = u.get('cache_read_input_tokens', 0) or 0
        cache_creation = u.get('cache_creation_input_tokens', 0) or 0
        input_tokens = regular + cache_read + cache_creation if regular is not None else None
        output_tokens = u.get('output_tokens', None)
        cached = cache_read
        reasoning = u.get('reasoning_tokens', 0) or 0
        total = input_tokens + output_tokens if input_tokens is not None and output_tokens is not None else None
    else: raise ValueError(f'unsupported provider {provider}')
    if input_tokens is None or output_tokens is None:
        raise ValueError(f'{provider} usage must include input and output tokens')
    vals = [input_tokens, output_tokens, cached, reasoning, total]
    if not all(isinstance(v, int) and v >= 0 for v in vals):
        raise ValueError('usage counts must be nonnegative integers')
    if cached > input_tokens or reasoning > output_tokens or total < input_tokens + output_tokens:
        raise ValueError('usage subsets/total are inconsistent')
    return {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cached_input_tokens': cached,
            'reasoning_tokens': reasoning, 'total_tokens': total}

def append_event(log_path: Path, event: dict) -> None:
    if event['stage'] not in STAGES:raise ValueError(f'unknown stage {event["stage"]}')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    # Prevent double counting a retried API response, but allow independent
    # requests in the same workflow stage when their request IDs differ.
    if event.get('request_id') and log_path.exists():
        key = (event.get('run_id'), event['stage'], event['request_id'])
        for existing in log_path.read_text(encoding='utf-8').splitlines():
            if not existing.strip():continue
            item=json.loads(existing)
            if (item.get('run_id'),item.get('stage'),item.get('request_id'))==key:
                if item.get('measurement') == event.get('measurement'):
                    return
                raise ValueError('reused request_id has a conflicting measurement type')
    event.setdefault('timestamp', dt.datetime.now(dt.timezone.utc).isoformat())
    # Only digests/numbers/metadata; never store potentially proprietary text.
    with log_path.open('a', encoding='utf-8') as f: f.write(json.dumps(event,ensure_ascii=False,sort_keys=True)+'\n')

def report(log_path: Path) -> dict:
    events=[json.loads(l) for l in log_path.read_text(encoding='utf-8').splitlines() if l.strip()]
    groups=defaultdict(lambda: {'events':0,'exact_input':0,'exact_output':0,'exact_cached':0,'exact_reasoning':0,'estimated_input':0,'estimated_output':0,'cache_hits':0,'local_only':0})
    for ev in events:
        g=groups[ev['stage']];g['events']+=1
        mode=ev.get('measurement')
        if mode=='exact':
            for k,j in [('input_tokens','exact_input'),('output_tokens','exact_output'),('cached_input_tokens','exact_cached'),('reasoning_tokens','exact_reasoning')]:g[j]+=ev['usage'].get(k,0)
        elif mode=='estimate':
            g['estimated_input']+=ev.get('input_tokens',0)
            g['estimated_output']+=ev.get('output_tokens',0)
        elif mode=='cache_hit':g['cache_hits']+=1
        elif mode=='local':g['local_only']+=1
        else:raise ValueError('unknown measurement method')
    exact=any(v['exact_input'] or v['exact_output'] for v in groups.values())
    estimated=any(v['estimated_input'] or v['estimated_output'] for v in groups.values())
    return {'schema_version':1,'source':str(log_path),'measurement':'mixed' if exact and estimated else 'exact' if exact else 'estimate' if estimated else 'local-only',
            'disclaimer':'ESTIMATES ARE NOT API BILLING; only exact events come from provider usage fields.',
            'stages':{name:groups[name] for name in STAGES if name in groups},
            'totals':{k:sum(row[k] for row in groups.values()) for k in ('exact_input','exact_output','exact_cached','exact_reasoning','estimated_input','estimated_output','cache_hits','local_only')}}

def main():
    p=argparse.ArgumentParser(description='Record API-exact or clearly estimated token usage by workflow stage')
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('record');a.add_argument('--log',type=Path,required=True);a.add_argument('--stage',choices=STAGES,required=True)
    a.add_argument('--provider',choices=['openai','anthropic']);a.add_argument('--usage-file',type=Path)
    a.add_argument('--prompt-file',type=Path,action='append',default=[]);a.add_argument('--response-file',type=Path,action='append',default=[])
    a.add_argument('--run-id',default='manual');a.add_argument('--request-id');a.add_argument('--cached',action='store_true');a.add_argument('--local',action='store_true')
    b=sub.add_parser('report');b.add_argument('--log',type=Path,required=True);b.add_argument('--out',type=Path)
    args=p.parse_args()
    if args.cmd=='report':
        result=report(args.log);raw=json.dumps(result,ensure_ascii=False,indent=2)
        if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(raw+'\n',encoding='utf-8')
        print(raw);return
    modes=sum([bool(args.usage_file),bool(args.prompt_file or args.response_file),args.cached,args.local])
    if modes!=1: p.error('choose exactly one usage-file, prompt/response files, --cached, or --local')
    base={'stage':args.stage,'run_id':args.run_id,'request_id':args.request_id}
    if args.usage_file:
        if not args.provider:p.error('provider is required with usage-file')
        base.update({'measurement':'exact','provider':args.provider,'usage':parse_usage(json.loads(args.usage_file.read_text(encoding='utf-8')),args.provider)})
    elif args.cached:base.update({'measurement':'cache_hit'})
    elif args.local:base.update({'measurement':'local'})
    else:
        before=file_measure(args.prompt_file);after=file_measure(args.response_file)
        base.update({'measurement':'estimate','input_tokens':before['estimated_tokens'],'output_tokens':after['estimated_tokens'],
                     'input_bytes':sum(f['bytes'] for f in before['files']),'output_bytes':sum(f['bytes'] for f in after['files']),
                     'fingerprint':hashlib.sha256((before['sha256']+after['sha256']).encode()).hexdigest(),'estimator':'cjk_1.25_ascii_div_3.1_v1'})
    append_event(args.log,base)
    print(json.dumps(base,ensure_ascii=False))
if __name__=='__main__':main()
