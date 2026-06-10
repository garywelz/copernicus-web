#!/usr/bin/env node
/**
 * Build graph-data.json for the Whole of Mathematics force-directed visualization.
 * Reads metadata.json, derives nodes and links from domainHierarchy and processes.
 *
 * When to run:
 *   - After editing metadata.json (adding/removing processes or subcategories)
 *   - After changing domainHierarchy or subcategoryToArxiv in metadata
 *
 * Run: node build-graph-data.js
 * Or:  ./rebuild-graph.sh
 *
 * The upload script (upload-mathematics-database-to-gcs.sh) runs this automatically
 * before uploading to GCS.
 */

const fs = require('fs');
const path = require('path');

const METADATA_PATH = path.join(__dirname, 'metadata.json');
const OUTPUT_PATH = path.join(__dirname, 'graph-data.json');

function buildGraphData() {
  const metadata = JSON.parse(fs.readFileSync(METADATA_PATH, 'utf8'));
  const { domainHierarchy, processes } = metadata;

  // Build subcategory -> domain mapping
  const subcategoryToDomain = {};
  for (const [domainId, domain] of Object.entries(domainHierarchy)) {
    for (const subcat of domain.subcategories || []) {
      subcategoryToDomain[subcat] = domainId;
    }
  }

  const nodes = [];
  const links = [];
  const nodeIds = new Set();

  function addNode(node) {
    if (!nodeIds.has(node.id)) {
      nodeIds.add(node.id);
      nodes.push(node);
    }
  }

  function addLink(source, target) {
    links.push({ source, target });
  }

  // Level 0: root
  addNode({
    id: 'root',
    name: 'Mathematics',
    level: 0,
    type: 'root'
  });

  // Level 1: domains
  for (const [domainId, domain] of Object.entries(domainHierarchy)) {
    const subcats = domain.subcategories || [];
    const processCount = processes.filter(p => subcats.includes(p.subcategory)).length;
    if (processCount === 0 && subcats.length === 0) continue; // skip empty domains

    addNode({
      id: domainId,
      name: domain.name,
      level: 1,
      type: 'domain',
      arxiv: domain.arxiv,
      processCount
    });
    addLink('root', domainId);
  }

  // Level 2: subcategories (only those with processes)
  const subcategoryProcessCount = {};
  for (const p of processes) {
    subcategoryProcessCount[p.subcategory] = (subcategoryProcessCount[p.subcategory] || 0) + 1;
  }

  for (const [subcatId, count] of Object.entries(subcategoryProcessCount)) {
    if (count === 0) continue;
    const domainId = subcategoryToDomain[subcatId];
    if (!domainId) continue; // skip subcategories not in any domain

    const subcatName = subcatId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    addNode({
      id: subcatId,
      name: subcatName,
      level: 2,
      type: 'subcategory',
      domain: domainId,
      processCount: count
    });
    addLink(domainId, subcatId);
  }

  // Level 3: processes
  for (const p of processes) {
    const domainId = subcategoryToDomain[p.subcategory];
    if (!domainId) continue;

    addNode({
      id: p.id,
      name: p.name,
      level: 3,
      type: 'process',
      processId: p.id,
      subcategory: p.subcategory,
      domain: domainId,
      processType: p.processType || 'axiomatic_theory',
      url: `processes/${p.subcategory}/${p.id}.html`
    });
    addLink(p.subcategory, p.id);
  }

  const graphData = {
    nodes,
    links,
    meta: {
      generatedAt: new Date().toISOString(),
      totalNodes: nodes.length,
      totalLinks: links.length,
      totalProcesses: processes.length
    }
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(graphData, null, 2), 'utf8');
  console.log(`Generated ${OUTPUT_PATH}: ${nodes.length} nodes, ${links.length} links`);
}

buildGraphData();
