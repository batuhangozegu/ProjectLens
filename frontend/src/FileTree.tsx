import { languageLabel } from './i18n';
import { useState } from 'react';
import type { FileRecord } from './api/client';

type TreeNode = { name: string; path: string; children: Map<string, TreeNode>; file?: FileRecord };

function buildTree(files: FileRecord[]) {
  const root: TreeNode = { name: '', path: '', children: new Map() };
  for (const file of [...files].sort((a, b) => a.path.localeCompare(b.path))) {
    const parts = file.path.split('/').filter(Boolean);
    let current = root;
    parts.forEach((part, index) => {
      let child = current.children.get(part);
      if (!child) { child = { name: part, path: parts.slice(0, index + 1).join('/'), children: new Map() }; current.children.set(part, child); }
      current = child;
    });
    current.file = file;
  }
  return root;
}

export function FileTree({ files, selectedPath, onSelect }: { files: FileRecord[]; selectedPath: string | null; onSelect: (path: string) => void }) {
  const tree = buildTree(files);
  const [closed, setClosed] = useState<Set<string>>(() => new Set());
  function renderNodes(node: TreeNode) {
    return <ul>{[...node.children.values()].map((child) => {
      const isDirectory = child.children.size > 0;
      return <li key={child.path}>
        {isDirectory && <button className="tree-folder" aria-expanded={!closed.has(child.path)} onClick={() => setClosed((previous) => { const next = new Set(previous); next.has(child.path) ? next.delete(child.path) : next.add(child.path); return next; })}>{closed.has(child.path) ? '▸' : '▾'} {child.name}/</button>}
        {child.file && <button className="tree-file" aria-current={selectedPath === child.path ? 'true' : undefined} onClick={() => onSelect(child.path)}><span aria-hidden="true">{isDirectory ? '↳ ' : ''}</span>{child.name}<small>{languageLabel(child.file.language)} · {child.file.physical_loc === null ? '—' : new Intl.NumberFormat('tr-TR').format(child.file.physical_loc)} satır</small></button>}
        {isDirectory && !closed.has(child.path) && renderNodes(child)}
      </li>;
    })}</ul>;
  }
  return <nav className="file-tree" aria-label="Depo dosyaları"><h2>Dosyalar <span>({new Intl.NumberFormat('tr-TR').format(files.length)})</span></h2>{files.length ? renderNodes(tree) : <p className="empty">Bu analizde dosya yok.</p>}</nav>;
}
