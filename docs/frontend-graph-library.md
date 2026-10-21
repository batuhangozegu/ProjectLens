# Frontend graph library decision

**Decision: use React Flow (`@xyflow/react`) for the first dependency graph UI.** Pin `12.11.5` in `frontend/package.json`; the package is MIT licensed.

| Candidate | License and React fit | Performance and layout | Accessibility |
| --- | --- | --- | --- |
| Cytoscape.js | MIT; mature canvas graph API, React integration is adapter-based | Strong graph rendering for thousands of nodes; built-in breadth of graph layouts and extensions | Canvas interaction requires deliberate keyboard and screen-reader support |
| React Flow / `@xyflow/react` | MIT; first-party React components and TypeScript types | SVG/DOM nodes are convenient for interactive file details; a few thousand nodes need viewport culling and careful rendering. Layout is supplied by integrations such as Dagre/ELK | Keyboard navigation and ARIA support provide a useful baseline |
| Sigma.js + graphology | MIT; React can host its canvas renderer, graphology models graph data | WebGL-oriented rendering suits larger graphs; layouts are typically provided by graphology packages | Canvas visualization needs separate accessible controls and an equivalent textual view |

For ProjectLens, cycle groups and per-file selection are central interactions. React Flow keeps node selection, details, and application state close to React, while its extensible layout integrations cover directed dependency layouts. At the expected scale, viewport rendering is a reasonable tradeoff; benchmark and revisit Cytoscape or Sigma if real repositories make interaction sluggish. Provide a file list/details panel as the accessible alternative to graph-only navigation.
