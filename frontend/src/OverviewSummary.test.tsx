import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import type { AnalysisResult } from './api/client';
import { OverviewSummary } from './OverviewSummary';

afterEach(cleanup);
const result: AnalysisResult = {
  schema_version: '1', files: [], dependency_edges: [], cycles: [], external_imports: [], unresolved_imports: [], frameworks: [], test_matches: [], partial: true,
  diagnostics: [{ stage: 'scan', file: 'lib/large.dart', error_type: 'FileTooLarge', message: '2048 bytes exceeds limit of 1024' }],
  metrics: {
    health: { score: 45, level: 'attention' },
    risk: { counts_by_level: { high: 1 }, top_risks: [{ path: 'lib/a.dart', level: 'high', factors: [{ reason: '12 commits in the history window' }] }] },
    findings: { top_findings: [
      { kind: 'large_function', reason: 'Function spans 160 lines; threshold is 80 lines.' },
      { kind: 'high_fan_out', reason: 'File has 17 distinct local dependencies; threshold is 15.' },
      { kind: 'many_members', reason: 'Class-like declaration has 32 direct methods; threshold is 30 methods.' },
    ] },
  },
};

describe('overview reading order', () => {
  it('leads with a verdict, three concerns and descriptive navigation', () => {
    render(<OverviewSummary result={result} projectId={4} />);
    expect(screen.getByRole('heading', { name: 'Bu projeyi anlamak için' })).toBeInTheDocument();
    expect(screen.getByText('Öncelikli inceleme gerekiyor.')).toBeInTheDocument();
    expect(screen.getByText('İlgi gerekiyor')).toBeInTheDocument();
    const concerns = screen.getByRole('region', { name: 'Öncelikli 3 konu' });
    expect(within(concerns).getAllByRole('listitem')).toHaveLength(3);
    expect(within(concerns).getByText('Yüksek risk: Geçmiş aralığında 12 commit')).toBeInTheDocument();
    expect(within(concerns).getByText('Uzun fonksiyon')).toBeInTheDocument();
    expect(within(concerns).queryByText('Çok sayıda metot')).not.toBeInTheDocument();
    const links = within(screen.getByRole('navigation', { name: 'Projeyi keşfedin' })).getAllByRole('link');
    expect(links).toHaveLength(4);
    expect(links[0]).toHaveAttribute('href', '#/projects/4/files');
    expect(links[0]).toHaveAccessibleName(/Dosyaların birbirini nasıl kullandığını görün/);
    expect(screen.getByText('Tarama · Dosya çok büyük')).toBeInTheDocument();
    expect(screen.getByText('2048 bayt, 1024 bayt sınırını aşıyor')).toBeInTheDocument();
    expect(screen.getByText('Kısmi analiz')).toBeInTheDocument();
  });

  it('keeps unknown health unavailable and does not invent a zero score', () => {
    render(<OverviewSummary result={{ ...result, metrics: {}, partial: false, diagnostics: [] }} projectId={4} />);
    expect(screen.getByText('Sağlık için yeterli veri yok.')).toBeInTheDocument();
    expect(screen.queryByText('/ 100')).not.toBeInTheDocument();
    expect(screen.getByText('Öncelikli konuları belirlemek için yeterli veri yok.')).toBeInTheDocument();
  });
});
