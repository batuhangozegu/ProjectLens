import { useEffect, useState } from 'react';

export function useRoute() {
  const [path, setPath] = useState(() => location.hash.slice(1) || '/');
  useEffect(() => {
    const update = () => setPath(location.hash.slice(1) || '/');
    addEventListener('hashchange', update);
    return () => removeEventListener('hashchange', update);
  }, []);
  const match = path.match(/^\/projects\/(\d+)$/);
  return { path, projectId: match ? Number(match[1]) : null };
}

export function navigate(path: string) { location.hash = path; }
