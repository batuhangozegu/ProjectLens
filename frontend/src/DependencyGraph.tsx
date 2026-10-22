import { useMemo } from 'react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { AnalysisResult } from './api/client';

export const GRAPH_NODE_LIMIT = 120;
function layout(paths: string[], edges: AnalysisResult['dependency_edges'], cycles: string[][]) {
  const group = new Map<string, number>();
  cycles.forEach((members, index) => members.forEach((path) => group.set(path, index)));
  const ordered = [...paths].sort((a, b) => a.localeCompare(b));
  const known = new Set(ordered);
  const outgoing = new Map(ordered.map((path) => [path, new Set<string>()]));
  const incoming = new Map(ordered.map((path) => [path, new Set<string>()]));
  for (const edge of edges) if (known.has(edge.source) && known.has(edge.target) && (!group.has(edge.source) || group.get(edge.source) !== group.get(edge.target))) { outgoing.get(edge.source)?.add(edge.target); incoming.get(edge.target)?.add(edge.source); }
  const layers = new Map(ordered.map((path) => [path, 0]));
  for (let pass = 0; pass < ordered.length; pass++) {
    let changed = false;
    for (const source of ordered) for (const target of outgoing.get(source) ?? []) {
      const next = Math.max(layers.get(target) ?? 0, (layers.get(source) ?? 0) + 1);
      if (next !== layers.get(target)) { layers.set(target, next); changed = true; }
    }
    if (!changed) break;
  }
  const groups = new Map<number, string[]>();
  for (const path of ordered) { const layer = layers.get(path) ?? 0; groups.set(layer, [...(groups.get(layer) ?? []), path]); }
  const coordinates = new Map<string, { x: number; y: number }>();
  for (const [layer, group] of groups) group.forEach((path, index) => coordinates.set(path, { x: layer * 260, y: index * 92 }));
  return coordinates;
}

export function DependencyGraph({ result, selectedPath, onSelect }: { result: AnalysisResult; selectedPath: string | null; onSelect: (path: string) => void }) {
  // Files without local dependency edges would only stack up as isolated boxes; the file tree lists them.
  const connectedFiles = useMemo(() => {
    const degree = new Map<string, number>();
    for (const edge of result.dependency_edges ?? []) for (const path of [edge.source, edge.target]) degree.set(path, (degree.get(path) ?? 0) + 1);
    return result.files.filter((file) => degree.has(file.path)).sort((a, b) => (degree.get(b.path) ?? 0) - (degree.get(a.path) ?? 0) || a.path.localeCompare(b.path));
  }, [result.files, result.dependency_edges]);
  const visibleFiles = useMemo(() => connectedFiles.slice(0, GRAPH_NODE_LIMIT), [connectedFiles]);
  const { nodes, edges } = useMemo(() => {
    const visiblePaths = new Set(visibleFiles.map((file) => file.path));
    const cyclePaths = new Set((result.cycles ?? []).flat());
    const positions = layout(visibleFiles.map((file) => file.path), result.dependency_edges ?? [], result.cycles ?? []);
    const nodes: Node[] = visibleFiles.map((file) => ({ id: file.path, position: positions.get(file.path) ?? { x: 0, y: 0 }, data: { label: `${file.path}\n${file.language || 'Unknown'} · ${file.physical_loc ?? '—'} LOC` }, style: { whiteSpace: 'pre-line', width: 210, border: cyclePaths.has(file.path) ? '2px solid #bd5429' : '1px solid #9aacc4', background: cyclePaths.has(file.path) ? '#fff0e8' : '#fff', color: '#172338', borderRadius: 8, padding: 10, cursor: 'pointer', ...(selectedPath === file.path ? { boxShadow: '0 0 0 3px #829fff' } : {}) } }));
    const edges: Edge[] = (result.dependency_edges ?? []).filter((edge) => visiblePaths.has(edge.source) && visiblePaths.has(edge.target)).map((edge, index) => ({ id: `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target, animated: false, style: { stroke: '#6a7d99' } }));
    return { nodes, edges };
  }, [visibleFiles, result.dependency_edges, result.cycles, selectedPath]);
  const omitted = connectedFiles.length - visibleFiles.length;
  const isolated = result.files.length - connectedFiles.length;
  return <section className="graph-section" aria-label="Bağımlılık grafiği">
    <p className="graph-key">Dosya seçmek için klavyeyle kullanılabilen depo dosya ağacını da kullanabilirsiniz.</p>
    {omitted > 0 && <p className="notice graph-notice" role="status">Grafikteki {connectedFiles.length} bağlantılı dosyanın {visibleFiles.length} tanesi gösteriliyor. {omitted} dosya gösterilmedi; tüm dosyaları seçmek için dosya ağacını kullanın.</p>}
    {isolated > 0 && visibleFiles.length > 0 && <p className="graph-key">{isolated} dosyanın yerel bağımlılığı yok; yalnızca dosya ağacında gösteriliyor.</p>}
    {visibleFiles.length ?<div className="graph-canvas"><ReactFlow nodes={nodes} edges={edges} minZoom={0.1} fitView fitViewOptions={{ padding: .2 }} onInit={(flow) => { setTimeout(() => void flow.fitView({ padding: .2 }), 50); }} nodesDraggable={false} nodesConnectable={false} onNodeClick={(_, node) => onSelect(node.id)} aria-label="Dosya bağımlılık grafiği"><Background color="#cbd5e1" gap={24} /><Controls /></ReactFlow></div> : <p className="empty">{result.files.length ? 'Analiz edilen dosyalar arasında yerel bağımlılık bulunamadı.' : 'Bağımlılık grafiğinde gösterilecek dosya yok.'}</p>}
    <p className="graph-key"><span className="cycle-swatch" aria-hidden="true" /> Vurgulanan düğümler bildirilen bir döngüye aittir.</p>
  </section>;
}
