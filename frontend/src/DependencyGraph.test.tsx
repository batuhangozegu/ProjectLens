import { describe, expect, it } from 'vitest';
import { graphLayout, graphAriaLabels } from './DependencyGraph';

describe('dependency graph layout and accessibility', () => {
  it('wraps large folders into multiple rows and keeps folders separate deterministically', () => {
    const paths = [...Array.from({ length: 12 }, (_, i) => `src/file-${i}.py`), 'tests/test_a.py'];
    const layout = graphLayout(paths);
    expect([...layout]).toEqual([...graphLayout([...paths].reverse())]);
    expect(new Set([...layout.values()].map(p => `${p.x}:${p.y}`)).size).toBe(paths.length);
    expect(Math.max(...[...layout.values()].map(p => p.x))).toBeLessThanOrEqual(600);
    expect(layout.get('tests/test_a.py')!.y).toBeGreaterThan(Math.max(...paths.filter(p => p.startsWith('src/')).map(p => layout.get(p)!.y)));
  });

  it('provides Turkish controls and keyboard descriptions', () => {
    expect(graphAriaLabels['controls.zoomIn.ariaLabel']).toBe('Yakınlaştır');
    expect(graphAriaLabels['controls.zoomOut.ariaLabel']).toBe('Uzaklaştır');
    expect(graphAriaLabels['controls.fitView.ariaLabel']).toBe('Grafiği ekrana sığdır');
    expect(graphAriaLabels['node.a11yDescription.default']).toContain('Enter veya boşluk');
    expect(graphAriaLabels['node.a11yDescription.ariaLiveMessage']({ direction: 'left', x: 1, y: 2 })).toBe('Dosya konumu: 1, 2');
  });
});
