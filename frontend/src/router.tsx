import { useEffect, useState } from 'react';

export function useRoute() {
  const [path, setPath] = useState(() => location.hash.slice(1) || '/');
  useEffect(() => {
    const update = () => setPath(location.hash.slice(1) || '/');
    addEventListener('hashchange', update);
    return () => removeEventListener('hashchange', update);
  }, []);
  const match = path.match(/^\/projects\/(\d+)$/);
  const filesMatch = path.match(/^\/projects\/(\d+)\/files\/?$/);
  return { path, projectId: match ? Number(match[1]) : filesMatch ? Number(filesMatch[1]) : null, files: Boolean(filesMatch) };
}

export function navigate(path: string) { location.hash = path; }
