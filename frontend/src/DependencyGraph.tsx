import { useMemo } from 'react';
import { Background, Controls, MarkerType, ReactFlow, type AriaLabelConfig, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { AnalysisResult } from './api/client';
import { languageLabel } from './i18n';

export const GRAPH_NODE_LIMIT = 120;
export const graphAriaLabels: AriaLabelConfig = {
  'node.a11yDescription.default': 'Dosya ayrıntılarını görmek için Enter veya boşluk tuşuna basın.',
  'node.a11yDescription.keyboardDisabled': 'Dosya ayrıntılarını görmek için Enter veya boşluk tuşuna basın.',
  'node.a11yDescription.ariaLiveMessage': ({ x, y }) => `Dosya konumu: ${x}, ${y}`,
  'edge.a11yDescription.default': 'Yerel dosya bağımlılığı.',
  'controls.ariaLabel': 'Grafik kontrolleri', 'controls.zoomIn.ariaLabel': 'Yakınlaştır', 'controls.zoomOut.ariaLabel': 'Uzaklaştır',
  'controls.fitView.ariaLabel': 'Grafiği ekrana sığdır', 'controls.interactive.ariaLabel': 'Grafik etkileşimini aç veya kapat',
  'minimap.ariaLabel': 'Grafik küçük haritası', 'handle.ariaLabel': 'Bağlantı noktası',
};

// A bounded grid of folder groups is deterministic even with dependency cycles.
export function graphLayout(paths: string[]) {
  const groups = new Map<string, string[]>();
  for (const path of [...paths].sort()) {
    const folder = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
    groups.set(folder, [...(groups.get(folder) ?? []), path]);
  }
  const positions = new Map<string, { x: number; y: number }>();
  let y = 0;
  for (const members of groups.values()) {
    members.forEach((path, i) => positions.set(path, { x: (i % 3) * 300, y: y + Math.floor(i / 3) * 160 }));
    y += Math.ceil(members.length / 3) * 160 + 70;
  }
  return positions;
}

export function DependencyGraph({ result, selectedPath, onSelect }: { result: AnalysisResult; selectedPath: string | null; onSelect: (path: string) => void }) {
  const connectedFiles = useMemo(() => {
    const degree = new Map<string, number>();
    for (const edge of result.dependency_edges ?? []) for (const path of [edge.source, edge.target]) degree.set(path, (degree.get(path) ?? 0) + 1);
    return result.files.filter(file => degree.has(file.path)).sort((a, b) => (degree.get(b.path) ?? 0) - (degree.get(a.path) ?? 0) || a.path.localeCompare(b.path));
  }, [result.files, result.dependency_edges]);
  const visibleFiles = useMemo(() => {
    const files = connectedFiles.slice(0, GRAPH_NODE_LIMIT);
    const selected = connectedFiles.find(file => file.path === selectedPath);
    if (selected && !files.includes(selected)) files[files.length - 1] = selected;
    return files;
  }, [connectedFiles, selectedPath]);
  const { nodes, edges } = useMemo(() => {
    const paths = new Set(visibleFiles.map(file => file.path));
    const cycles = new Set((result.cycles ?? []).flat());
    const positions = graphLayout([...paths]);
    const nodes: Node[] = visibleFiles.map(file => {
      const name = file.path.split('/').pop();
      const folder = file.path.includes('/') ? file.path.slice(0, file.path.lastIndexOf('/')) : 'Depo kökü';
      const cycle = cycles.has(file.path);
      return { id: file.path, position: positions.get(file.path)!, selected: selectedPath === file.path,
        ariaLabel: `${file.path} · ${languageLabel(file.language)}${cycle ? ' · Döngüde' : ''}`,
        className: `file-node${cycle ? ' in-cycle' : ''}`, style: { width: 240 },
        data: { label: <div title={`${file.path} · ${file.physical_loc ?? 'Bilinmiyor'} LOC${cycle ? ' · Bağımlılık döngüsünde' : ''}`}><strong>{name}</strong><small>{folder}</small><small>{languageLabel(file.language)} · {file.physical_loc ?? '—'} LOC{cycle ? ' · ↻ Döngüde' : ''}</small></div> },
      };
    });
    const edges: Edge[] = (result.dependency_edges ?? []).filter(edge => paths.has(edge.source) && paths.has(edge.target)).map((edge, i) => ({
      id: `${edge.source}-${edge.target}-${i}`, source: edge.source, target: edge.target, animated: false,
      ariaLabel: `${edge.source}, ${edge.target} dosyasını kullanır`, markerEnd: { type: MarkerType.ArrowClosed },
    }));
    return { nodes, edges };
  }, [visibleFiles, result.dependency_edges, result.cycles, selectedPath]);
  const omitted = connectedFiles.length - visibleFiles.length;
  const isolated = result.files.length - connectedFiles.length;
  return <section className="graph-section" aria-label="Bağımlılık grafiği">
    <h2>Dosyalar nasıl bağlanıyor?</h2><p>Bir dosyaya tıklayarak ayrıntıları görün. Yakınlaştırma düğmeleriyle ölçeği değiştirin; boş alanı sürükleyerek gezinin. Klavyeyle dosya seçmek için dosya ağacını da kullanabilirsiniz.</p>
    <div className="graph-legend" aria-label="Grafik açıklaması"><span>→ Ok: kullanan dosyadan kullanılan dosyaya</span><span><span className="cycle-swatch" aria-hidden="true" /> ↻ Döngüde</span><span>▣ Seçili dosya</span><span>Dosyalar klasöre göre gruplanır.</span></div>
    {omitted > 0 && <p className="notice" role="status">{connectedFiles.length} bağlantılı dosyanın {visibleFiles.length} tanesi gösteriliyor. {omitted} dosya gizli; tüm dosyalar için dosya ağacını kullanın.</p>}
    {isolated > 0 && visibleFiles.length > 0 && <p className="graph-key">{isolated} dosyanın yerel bağımlılığı yok; yalnızca dosya ağacında gösteriliyor.</p>}
    {visibleFiles.length ? <div className="graph-canvas"><ReactFlow nodes={nodes} edges={edges} ariaLabelConfig={graphAriaLabels} minZoom={0.1} fitView fitViewOptions={{ padding: .15, maxZoom: 1 }} nodesDraggable={false} nodesConnectable={false} edgesFocusable={false} deleteKeyCode={null} colorMode="system" onSelectionChange={({ nodes }) => { if (nodes[0]) onSelect(nodes[0].id); }} onNodeClick={(_, node) => onSelect(node.id)} aria-label="Dosya bağımlılık grafiği"><Background gap={24} /><Controls showInteractive={false} /></ReactFlow></div> : <p className="empty">{result.files.length ? 'Analiz edilen dosyalar arasında yerel bağımlılık bulunamadı.' : 'Bağımlılık grafiğinde gösterilecek dosya yok.'}</p>}
  </section>;
}
