// Type declarations for cytoscape-dagre
declare module 'cytoscape-dagre' {
  import cytoscape from 'cytoscape';
  
  function dagre(cytoscape: typeof import('cytoscape')): void;
  
  export default dagre;
}

// Extend Cytoscape layout options to include dagre-specific options
declare module 'cytoscape' {
  interface BaseLayoutOptions {
    rankDir?: 'TB' | 'BT' | 'LR' | 'RL';
    nodeSep?: number;
    edgeSep?: number;
    rankSep?: number;
    spacingFactor?: number;
  }
}

