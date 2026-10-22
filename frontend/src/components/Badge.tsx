import type { ReactNode } from 'react';

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  const icon = ['high', 'critical', 'poor', 'attention', 'BLOCKED'].includes(tone) ? '▲' : ['good', 'excellent', 'DONE', 'succeeded', 'completed'].includes(tone) ? '✓' : '●';
  return <span className={`badge badge-${tone.toLowerCase()}`}><span aria-hidden="true">{icon}</span> {children}</span>;
}
