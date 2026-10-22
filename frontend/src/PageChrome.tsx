import { useEffect, type ReactNode } from 'react';
import { dateLabel, snapshotStatusLabel, tr } from './i18n';
import type { ProjectSummary } from './api/client';
import { Badge } from './components/Badge';

const sections = [
  [tr.nav.overview, ''], [tr.nav.files, '/files'], [tr.nav.insights, '/insights'], [tr.nav.roadmap, '/roadmap'], [tr.nav.ai, '/ai'],
] as const;

export function SiteHeader() {
  return <header className="site-header"><a className="brand" href="#/" aria-label="ProjectLens ana sayfa"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header>;
}

export function ProjectNavigation({ projectId, current }: { projectId: number; current: string }) {
  return <nav className="project-nav" aria-label="Proje gezintisi">{sections.map(([label, suffix]) => <a key={label} href={`#/projects/${projectId}${suffix}`} aria-current={current === label ? 'page' : undefined}>{label}</a>)}</nav>;
}

export function PageFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const target = document.querySelector<HTMLElement>('main[tabindex="-1"]');
    target?.focus({ preventScroll: true });
  }, []);
  return <><a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); document.querySelector<HTMLElement>('main[tabindex="-1"]')?.focus(); }}>Ana içeriğe geç</a>{children}</>;
}

export function ProjectPageChrome({ projectId, current, project }: { projectId: number; current: string; project?: ProjectSummary | null }) {
  const snapshot = project?.latest_snapshot;
  return <div className="project-chrome"><SiteHeader />{project && <header className="project-context"><div><a href="#/" className="all-projects">← Tüm projeler</a><strong>{project.name}</strong>{project.repository_url && /^https:\/\/github\.com\//i.test(project.repository_url) && <a href={project.repository_url} target="_blank" rel="noreferrer">GitHub deposunu aç ↗</a>}</div><div className="context-meta"><span>Son analiz: {snapshot ? <time dateTime={snapshot.created_at}>{dateLabel(snapshot.created_at)}</time> : 'Henüz analiz yok'}</span><Badge tone={snapshot?.partial ? 'attention' : snapshot?.status}>{snapshot ? snapshotStatusLabel(snapshot.partial ? 'partial' : snapshot.status) : 'Analiz bekliyor'}</Badge></div></header>}<ProjectNavigation projectId={projectId} current={current} /></div>;
}
