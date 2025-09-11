#!/usr/bin/env python
"""Lightweight import dependency graph generator.

Scans the Main/ and DB/ packages for intra-project imports and emits a mermaid graph.
Intended for quick architectural visualization and AI agent consumption.
"""
from __future__ import annotations
import os, re, sys, pathlib, json
from collections import defaultdict

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_DIRS = ['Main','DB']
IMPORT_RE = re.compile(r'^from\s+([\w\.]+)\s+import|^import\s+([\w\.]+)', re.MULTILINE)

nodes = set()
edges = defaultdict(set)

for td in TARGET_DIRS:
    base = PROJECT_ROOT/td
    for path, _, files in os.walk(base):
        for f in files:
            if not f.endswith('.py'): continue
            fp = pathlib.Path(path)/f
            rel_mod = fp.relative_to(PROJECT_ROOT).with_suffix('').as_posix().replace('/', '.')
            try:
                text = fp.read_text(encoding='utf-8')
            except Exception:
                continue
            nodes.add(rel_mod)
            for m in IMPORT_RE.finditer(text):
                target = m.group(1) or m.group(2)
                if not target: continue
                if target.startswith(('Main','DB')) and target != rel_mod:
                    edges[rel_mod].add(target.split('.')[0:4][0])  # coarse first segment

mermaid_lines = ["graph LR"]
for src, tgts in edges.items():
    for tgt in tgts:
        mermaid_lines.append(f"  {src.replace('.','_')}--> {tgt.replace('.','_')}")

output = {
    'nodes': sorted(nodes),
    'edges': {k: sorted(v) for k,v in edges.items()},
    'mermaid': '\n'.join(mermaid_lines)
}

out_file = PROJECT_ROOT/'runtime_logs'/'dependency_graph.json'
out_file.write_text(json.dumps(output, indent=2))
print(f"Wrote graph data to {out_file}")

md_file = PROJECT_ROOT/'MD'/'DEPENDENCY_GRAPH.md'
md_file.write_text("""# Dependency Graph (Generated)\n\n```mermaid\n""" + output['mermaid'] + "\n```\n")
print(f"Wrote mermaid graph to {md_file}")
