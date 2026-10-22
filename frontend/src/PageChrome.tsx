import { useEffect, type ReactNode } from 'react';
import { tr } from './i18n';

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
  return <><a className="skip-link" href="#main-content">Ana içeriğe geç</a>{children}</>;
}

export function ProjectPageChrome({ projectId, current }: { projectId: number; current: string }) {
  return <><SiteHeader /><ProjectNavigation projectId={projectId} current={current} /></>;
}
