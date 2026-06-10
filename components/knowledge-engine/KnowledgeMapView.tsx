/**
 * Knowledge Map Visualization Component
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useEffect, useRef, useState, startTransition } from 'react'

// API base URL - adjust for production
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app'

type ContentTypesState = {
  papers: boolean
  processes: boolean
  videos: boolean
  podcasts: boolean
}

type DisciplinesState = {
  biology: boolean
  chemistry: boolean
  physics: boolean
  mathematics: boolean
  computer_science: boolean
  interdisciplinary: boolean
}

type SourcesState = {
  pubmed: boolean
  arxiv: boolean
  nasa_ads: boolean
  crossref: boolean
  youtube: boolean
  rss: boolean
}

type MapFilterOverrides = {
  contentTypes?: ContentTypesState
  disciplines?: DisciplinesState
  sources?: SourcesState
  dateRange?: { start: string; end: string }
  keywordSearch?: string
  maxPapers?: number
}

export default function KnowledgeMapView() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false) // Start as false - user clicks "Reload Map" to load
  const [error, setError] = useState<string | null>(null)
  const [maxPapers, setMaxPapers] = useState(10) // Start with smaller dataset for faster loading
  const [includeConcepts, setIncludeConcepts] = useState(true)
  const [includeSimilarity, setIncludeSimilarity] = useState(true)
  const [includeCategories, setIncludeCategories] = useState(true)
  const [stats, setStats] = useState({ nodes: 0, edges: 0, papers: 0, concepts: 0 })
  const cyRef = useRef<any>(null)
  const [selectedNode, setSelectedNode] = useState<{ id: string; type: string; label: string } | null>(null)
  const [nodeExplanation, setNodeExplanation] = useState<string | null>(null)
  const [nodeExplanationLoading, setNodeExplanationLoading] = useState(false)
  const [nodeExplanationError, setNodeExplanationError] = useState<string | null>(null)
  
  // New filter states
  const [contentTypes, setContentTypes] = useState({
    papers: true,
    processes: false,
    videos: false,
    podcasts: false,
  })
  const [disciplines, setDisciplines] = useState({
    biology: false,
    chemistry: false,
    physics: false,
    mathematics: false,
    computer_science: false,
    interdisciplinary: false,
  })
  const [sources, setSources] = useState({
    pubmed: false,
    arxiv: false,
    nasa_ads: false,
    crossref: false,
    youtube: false,
    rss: false,
  })
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const [keywordSearch, setKeywordSearch] = useState('')
  const [nodeSizeBy, setNodeSizeBy] = useState<'uniform' | 'citations' | 'relevance' | 'date'>('uniform')
  const [colorBy, setColorBy] = useState<'discipline' | 'content_type' | 'date' | 'source'>('discipline')
  const [showInstructions, setShowInstructions] = useState(false)

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return
    
    // Don't auto-load - user must click "Reload Map" to load the graph
    // This ensures the page starts with 0 stats and gives user control
    
    // Cleanup function
    return () => {
      // Clean up Cytoscape instance on unmount
      if (cyRef.current) {
        try {
          // Clear state first
          setSelectedNode(null)
          setNodeExplanation(null)
          
          // Remove all event listeners
          cyRef.current.off('tap', 'node')
          
          // Destroy Cytoscape instance
          cyRef.current.destroy()
          cyRef.current = null
          
          // Clear container DOM - use requestAnimationFrame to avoid React reconciliation conflicts
          if (containerRef.current) {
            requestAnimationFrame(() => {
              if (containerRef.current) {
                containerRef.current.innerHTML = ''
              }
            })
          }
        } catch (err) {
          console.debug('Error destroying Cytoscape instance on unmount:', err)
          // Force clear on error
          cyRef.current = null
          if (containerRef.current) {
            containerRef.current.innerHTML = ''
          }
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  
  // Clear graph when filters change (but don't auto-reload)
  // This prevents showing stale data from previous filters
  useEffect(() => {
    // Clear the graph when filters change, but only if graph is already loaded
    if (cyRef.current && containerRef.current) {
      try {
        // Clear selected node state first to prevent React from trying to render explanation for destroyed node
        setSelectedNode(null)
        setNodeExplanation(null)
        setNodeExplanationError(null)
        
        // Remove all event listeners before destroying
        cyRef.current.off('tap', 'node')
        
        // Destroy Cytoscape instance
        cyRef.current.destroy()
        cyRef.current = null
        
        // Clear container DOM - use requestAnimationFrame to avoid React reconciliation conflicts
        if (containerRef.current) {
          requestAnimationFrame(() => {
            if (containerRef.current) {
              containerRef.current.innerHTML = ''
            }
          })
        }
        
        // Reset stats to indicate filters have changed
        setStats({ nodes: 0, edges: 0, papers: 0, concepts: 0 })
        setError(null)
      } catch (err) {
        console.debug('Error clearing graph on filter change:', err)
        // Force clear on error
        cyRef.current = null
        if (containerRef.current) {
          containerRef.current.innerHTML = ''
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentTypes, disciplines, sources, dateRange, maxPapers, nodeSizeBy, colorBy])
  
  // Note: We don't auto-reload on filter changes - user clicks "Reload Map" button
  // This prevents too many API calls while user is adjusting filters

  const runQuickExample = (overrides: MapFilterOverrides) => {
    const nextContentTypes = overrides.contentTypes ?? contentTypes
    const nextDisciplines = overrides.disciplines ?? disciplines
    const nextSources = overrides.sources ?? sources
    const nextDateRange = overrides.dateRange ?? dateRange
    const nextKeyword = overrides.keywordSearch ?? keywordSearch
    const nextMaxPapers = overrides.maxPapers ?? maxPapers

    setContentTypes(nextContentTypes)
    setDisciplines(nextDisciplines)
    setSources(nextSources)
    setDateRange(nextDateRange)
    setKeywordSearch(nextKeyword)
    if (overrides.maxPapers !== undefined) {
      setMaxPapers(nextMaxPapers)
    }

    void loadKnowledgeMap({
      contentTypes: nextContentTypes,
      disciplines: nextDisciplines,
      sources: nextSources,
      dateRange: nextDateRange,
      keywordSearch: nextKeyword,
      maxPapers: nextMaxPapers,
    })
  }

  const loadKnowledgeMap = async (overrides?: MapFilterOverrides) => {
    const activeContentTypes = overrides?.contentTypes ?? contentTypes
    const activeDisciplines = overrides?.disciplines ?? disciplines
    const activeSources = overrides?.sources ?? sources
    const activeDateRange = overrides?.dateRange ?? dateRange
    const activeKeywordSearch = overrides?.keywordSearch ?? keywordSearch
    const activeMaxPapers = overrides?.maxPapers ?? maxPapers
    // Ensure we're on the client side
    if (typeof window === 'undefined') {
      console.warn('loadKnowledgeMap called on server side, skipping')
      return
    }

    if (!containerRef.current) {
      console.warn('Container ref not available yet, retrying...')
      // Retry after a delay - container might not be mounted yet with dynamic imports
      let attempts = 0
      const maxAttempts = 5
      const retry = () => {
        attempts++
        if (containerRef.current) {
          loadKnowledgeMap()
        } else if (attempts < maxAttempts) {
          setTimeout(retry, 300)
        } else {
          console.error('Container ref still not available after', maxAttempts, 'retries')
          setError('Failed to access graph container. Please refresh the page.')
          setLoading(false)
        }
      }
      setTimeout(retry, 300)
      return
    }

    // CRITICAL: Clean up existing Cytoscape instance before creating a new one
    // This prevents React from trying to remove DOM nodes that Cytoscape has already removed
    if (cyRef.current) {
      try {
        console.log('Cleaning up existing Cytoscape instance before reload...')
        // Clear state first
        setSelectedNode(null)
        setNodeExplanation(null)
        setNodeExplanationError(null)
        
        // Remove all event listeners
        cyRef.current.off('tap', 'node')
        
        // Destroy Cytoscape instance
        cyRef.current.destroy()
        cyRef.current = null
        
        // Clear container DOM synchronously (before async fetch)
        if (containerRef.current) {
          containerRef.current.innerHTML = ''
        }
      } catch (err) {
        console.warn('Error cleaning up existing Cytoscape instance:', err)
        // Force clear on error
        cyRef.current = null
        if (containerRef.current) {
          containerRef.current.innerHTML = ''
        }
      }
    }

    setLoading(true)
    setError(null)
    console.log('Loading knowledge map from:', `${API_BASE_URL}/api/knowledge-map/graph`)

    try {
      // Load Cytoscape dynamically to avoid SSR issues
      const cytoscapeModule = await import('cytoscape')
      const dagreModule = await import('cytoscape-dagre')
      const cytoscape = cytoscapeModule.default as any
      const dagre = dagreModule.default
      cytoscape.use(dagre)

      // Fetch graph data with filters
      const params = new URLSearchParams({
        max_papers: activeMaxPapers.toString(),
        include_concepts: includeConcepts.toString(),
        include_similarity: includeSimilarity.toString(),
        include_categories: includeCategories.toString(),
        format: 'cytoscape',
      })

      // Add content type filters
      if (activeContentTypes.papers) params.append('content_types', 'papers')
      if (activeContentTypes.processes) params.append('content_types', 'processes')
      if (activeContentTypes.videos) params.append('content_types', 'videos')
      if (activeContentTypes.podcasts) params.append('content_types', 'podcasts')

      // Add discipline filters
      const selectedDisciplines = Object.entries(activeDisciplines)
        .filter(([_, selected]) => selected)
        .map(([key, _]) => key)
      if (selectedDisciplines.length > 0) {
        params.append('disciplines', selectedDisciplines.join(','))
      }

      // Add source filters
      const selectedSources = Object.entries(activeSources)
        .filter(([_, selected]) => selected)
        .map(([key, _]) => key)
      if (selectedSources.length > 0) {
        params.append('sources', selectedSources.join(','))
      }

      // Add date range
      if (activeDateRange.start) params.append('date_start', activeDateRange.start)
      if (activeDateRange.end) params.append('date_end', activeDateRange.end)

      if (activeKeywordSearch.trim()) {
        params.append('keyword', activeKeywordSearch.trim())
      }

      // Add visualization options
      params.append('node_size_by', nodeSizeBy)
      params.append('color_by', colorBy)

      // Force rebuild if any filters are active (ensures we get fresh data matching filters)
      const hasFilters = selectedDisciplines.length > 0 || selectedSources.length > 0 ||
                         activeDateRange.start || activeDateRange.end || activeKeywordSearch.trim()
      params.append('force_rebuild', hasFilters ? 'true' : 'false')

      const url = `${API_BASE_URL}/api/knowledge-map/graph?${params}`
      console.log('Fetching from:', url)
      
      // Graph builds can take 60–90s on first load with filters; allow enough time.
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 120000)
      
      const response = await fetch(url, { signal: controller.signal })
      clearTimeout(timeoutId)
      console.log('Response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('API error:', response.status, errorText)
        throw new Error(`Failed to load knowledge map: ${response.status} ${response.statusText} - ${errorText}`)
      }

      const data = await response.json()
      console.log('Knowledge map data received:', { 
        hasNodes: !!data.nodes, 
        hasEdges: !!data.edges,
        nodeCount: data.nodes?.length || 0,
        edgeCount: data.edges?.length || 0,
        dataKeys: Object.keys(data)
      })

      // Destroy existing instance with proper cleanup (if not already done at start of function)
      if (cyRef.current) {
        try {
          console.log('Cleaning up existing Cytoscape instance before creating new one...')
          // Clear state first to prevent React from trying to render explanation for destroyed node
          setSelectedNode(null)
          setNodeExplanation(null)
          setNodeExplanationError(null)
          
          // Remove all event listeners
          cyRef.current.off('tap', 'node')
          
          // Destroy Cytoscape instance
          cyRef.current.destroy()
          cyRef.current = null
        } catch (err) {
          console.debug('Error destroying existing Cytoscape instance:', err)
          cyRef.current = null
        }
      }

      // Clear container DOM synchronously BEFORE processing data
      // This prevents React from trying to reconcile while Cytoscape DOM exists
      if (containerRef.current) {
        const container = containerRef.current
        // Clear synchronously - React won't try to manage this since we use dangerouslySetInnerHTML
        // Remove all children one by one to avoid React issues
        while (container.firstChild) {
          try {
            container.removeChild(container.firstChild)
          } catch (e) {
            // If removeChild fails (node already removed), force clear and break
            container.innerHTML = ''
            break
          }
        }
      }

      // Convert API response to Cytoscape format
      // API returns { nodes: [...], edges: [...] } in Cytoscape format already
      const elements: any[] = []
      
      // Add nodes first
      const nodeIds = new Set<string>()
      if (data.nodes && Array.isArray(data.nodes) && data.nodes.length > 0) {
        // Validate node format
        const validNodes = data.nodes.filter((node: any) => {
          if (!node.data || !node.data.id) {
            console.warn('Invalid node format:', node)
            return false
          }
          nodeIds.add(node.data.id)
          return true
        })
        elements.push(...validNodes)
        console.log(`Added ${validNodes.length} nodes to graph (${data.nodes.length - validNodes.length} invalid)`)
      } else {
        // Handle empty graph case - don't create Cytoscape instance
        console.log('No nodes found in API response - showing empty state')
        // Update state in a way that doesn't trigger DOM reconciliation issues
        setSelectedNode(null)
        setNodeExplanation(null)
        setNodeExplanationError(null)
        startTransition(() => {
          setStats({ nodes: 0, edges: 0, papers: 0, concepts: 0 })
          setLoading(false)
          setError('No papers found matching your filters. Try broadening your search criteria.')
        })
        return // Exit early - no graph to create
      }
      
      // Add edges - only those that reference existing nodes
      if (data.edges && Array.isArray(data.edges)) {
        // Validate edge format and ensure source/target nodes exist
        const invalidEdgeCount = { missingSource: 0, missingTarget: 0, invalidFormat: 0 }
        const validEdges = data.edges.filter((edge: any) => {
          if (!edge.data || !edge.data.source || !edge.data.target) {
            invalidEdgeCount.invalidFormat++
            return false
          }
          // Check if both source and target nodes exist
          if (!nodeIds.has(edge.data.source)) {
            invalidEdgeCount.missingSource++
            return false
          }
          if (!nodeIds.has(edge.data.target)) {
            invalidEdgeCount.missingTarget++
            return false
          }
          return true
        })
        elements.push(...validEdges)
        const totalInvalid = invalidEdgeCount.missingSource + invalidEdgeCount.missingTarget + invalidEdgeCount.invalidFormat
        if (totalInvalid > 0) {
          console.debug(`Filtered out ${totalInvalid} invalid edges (${invalidEdgeCount.missingSource} missing source, ${invalidEdgeCount.missingTarget} missing target, ${invalidEdgeCount.invalidFormat} invalid format)`)
        }
        console.log(`Added ${validEdges.length} edges to graph (${totalInvalid} filtered out)`)
      } else {
        console.warn('No edges found in API response:', data)
      }
      
      if (elements.length === 0) {
        // Handle empty results gracefully - don't throw error, show message instead
        setLoading(false)
        setError('No papers found matching your filters. Try broadening your search criteria (remove some filters, use a broader date range, or try different keywords).')
        // Clear any existing graph
        if (cyRef.current) {
          try {
            cyRef.current.destroy()
            cyRef.current = null
          } catch (err) {
            console.debug('Error destroying Cytoscape on empty result:', err)
          }
        }
        if (containerRef.current) {
          containerRef.current.innerHTML = ''
        }
        return
      }
      
      console.log(`Total elements for Cytoscape: ${elements.length}`)

      // Ensure container exists and has dimensions before initializing Cytoscape
      if (!containerRef.current) {
        throw new Error('Container ref is null - cannot initialize Cytoscape')
      }

      const container = containerRef.current
      const containerRect = container.getBoundingClientRect()
      if (containerRect.width === 0 || containerRect.height === 0) {
        console.warn('Container has zero dimensions, waiting for layout...')
        // Wait a frame for layout to settle
        await new Promise(resolve => requestAnimationFrame(resolve))
        const rect = container.getBoundingClientRect()
        if (rect.width === 0 || rect.height === 0) {
          throw new Error('Container still has zero dimensions after layout - cannot initialize Cytoscape')
        }
      }

      console.log('Container dimensions:', containerRect.width, 'x', containerRect.height)

      // Create new Cytoscape instance
      cyRef.current = cytoscape({
        container: container,
        elements: elements,
        style: [
          {
            selector: 'node[type="paper"]',
            style: {
              'background-color': '#3498db',
              'label': 'data(label)',
              'width': 30,
              'height': 30,
              'font-size': '10px',
              'text-wrap': 'wrap',
              'text-max-width': '150px',
              'text-valign': 'center',
              'text-halign': 'center',
              'color': '#2c3e50',
              'shape': 'ellipse',
              'border-width': 2,
              'border-color': '#2980b9',
            },
          },
          {
            selector: 'node[type="concept"]',
            style: {
              'background-color': '#e74c3c',
              'label': 'data(label)',
              'width': 40,
              'height': 40,
              'shape': 'diamond',
              'font-size': '12px',
              'font-weight': 'bold',
              'color': '#2c3e50',
              'border-width': 2,
              'border-color': '#c0392b',
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#95a5a6',
              'target-arrow-color': '#95a5a6',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'opacity': 0.6,
            },
          },
          {
            selector: 'edge[type="similarity"]',
            style: {
              'line-color': '#3498db',
              'target-arrow-color': '#3498db',
              'opacity': 0.4,
            },
          },
          {
            selector: 'edge[type="same_category"]',
            style: {
              'line-color': '#2ecc71',
              'target-arrow-color': '#2ecc71',
            },
          },
          {
            selector: 'edge[type="category"]',
            style: {
              'line-color': '#2ecc71',
              'target-arrow-color': '#2ecc71',
            },
          },
          {
            selector: 'edge[type="citation"]',
            style: {
              'line-color': '#e74c3c',
              'target-arrow-color': '#e74c3c',
            },
          },
        ],
        layout: {
          name: 'dagre',
          rankDir: 'TB',
          spacingFactor: 1.5,
        },
      })

      // Add event listeners
      cyRef.current.on('tap', 'node', async (evt: any) => {
        const node = evt.target
        const data = node.data()
        console.log('Node clicked:', data)

        const nodeId = data.id || data.paper_id || data.concept_id
        const nodeType = data.type || data.nodeType || 'unknown'
        const nodeLabel = data.label || data.title || 'Untitled'

        if (!nodeId) {
          console.warn('Clicked node has no id - skipping explanation')
          return
        }

        setSelectedNode({ id: nodeId, type: nodeType, label: nodeLabel })
        setNodeExplanation(null)
        setNodeExplanationError(null)
        setNodeExplanationLoading(true)

        try {
          // Build a focused question for the RAG endpoint
          let question = ''
          let mode: 'general' | 'paper_explanation' | 'concept_explanation' = 'general'

          if (nodeType === 'paper') {
            mode = 'paper_explanation'
            question = `Explain the main ideas, methods, and significance of this research paper: "${nodeLabel}". Use clear language suitable for an interdisciplinary research audience.`
          } else if (nodeType === 'concept') {
            mode = 'concept_explanation'
            const conceptName = nodeLabel || nodeId.replace('concept:', '')
            question = `Explain the concept "${conceptName}" and how it appears in the context of the mathematics and related research papers in this knowledge graph.`
          } else {
            mode = 'general'
            question = `Explain the node "${nodeLabel}" in the context of this scientific knowledge graph.`
          }

          const params = new URLSearchParams({
            question,
            max_context_items: '8',
            mode,
            content_types: 'papers,podcasts,glmp,math,chemistry,physics,computer_science,biology',
          })
          params.set('focus_id', nodeId)

          const url = `${API_BASE_URL}/api/rag/answer?${params.toString()}`
          console.log('Fetching node explanation from:', url)

          const response = await fetch(url)
          if (!response.ok) {
            const errorText = await response.text()
            console.error('RAG explanation error:', response.status, errorText)
            throw new Error(`Failed to get explanation: ${response.status} ${response.statusText}`)
          }

          const result = await response.json()
          setNodeExplanation(result.answer || 'No explanation generated.')
        } catch (err: any) {
          console.error('Error fetching node explanation:', err)
          setNodeExplanationError(err.message || 'Failed to load explanation.')
        } finally {
          setNodeExplanationLoading(false)
        }
      })

      // Calculate stats
      const nodes = data.nodes || []
      const edges = data.edges || []
      const papers = nodes.filter((n: any) => n.data?.type === 'paper').length
      const concepts = nodes.filter((n: any) => n.data?.type === 'concept').length

      // Fit the graph to viewport first
      if (cyRef.current) {
        cyRef.current.fit(undefined, 50) // 50px padding
        console.log('Graph fitted to viewport')
      }

      // Use requestAnimationFrame to delay state updates until after Cytoscape has finished
      // all DOM operations and the browser has painted. This prevents React from trying to
      // reconcile while Cytoscape is managing the DOM.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Double RAF ensures we're after paint
          startTransition(() => {
            setStats({
              nodes: nodes.length,
              edges: edges.length,
              papers,
              concepts,
            })
            setLoading(false)
          })
        })
      })

      console.log('Knowledge map loaded successfully!', {
        nodes: nodes.length,
        edges: edges.length,
        papers,
        concepts
      })
    } catch (err: any) {
      console.error('Error loading knowledge map:', err)
      const errorMessage = err.message || 'Failed to load knowledge map'
      console.error('Full error:', err)
      
      // Check if it's a timeout
      if (err.name === 'AbortError') {
        setError('Request timed out after 2 minutes. Try a Quick Example, reduce "Max Papers" to 10, or use a keyword to speed up retrieval.')
      } else {
        setError(`${errorMessage}. Check browser console (F12) for details. API: ${API_BASE_URL}`)
      }
      setLoading(false)
    }
  }

  const resetView = () => {
    if (cyRef.current) {
      try {
        cyRef.current.fit()
        cyRef.current.center()
        // Add visual feedback
        console.log('View reset - map centered and fitted')
      } catch (err) {
        console.debug('Error resetting view:', err)
      }
    } else {
      console.warn('Cannot reset view - map not loaded yet')
    }
  }

  const runUserSearch = () => {
    const query = keywordSearch.trim()
    if (!query) {
      setError('Enter a topic, question, or keyword phrase to build a knowledge map.')
      return
    }
    setError(null)
    void loadKnowledgeMap({ keywordSearch: query })
  }

  const clearHighlights = () => {
    if (cyRef.current) {
      try {
        const highlighted = cyRef.current.elements('.highlighted')
        highlighted.removeClass('highlighted')
        console.log(`Cleared highlights from ${highlighted.length} elements`)
      } catch (err) {
        console.debug('Error clearing highlights:', err)
      }
    } else {
      console.warn('Cannot clear highlights - map not loaded yet')
    }
  }

  return (
    <div className="space-y-4">
      {/* Instructions Toggle */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-blue-900">📖 How to Use the Knowledge Map</h3>
            <p className="text-xs text-blue-700 mt-1">
              Search for a topic, then refine with optional filters below
            </p>
          </div>
          <button
            onClick={() => setShowInstructions(!showInstructions)}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            {showInstructions ? 'Hide' : 'Show'} Instructions
          </button>
        </div>
        {showInstructions && (
          <div className="mt-4 text-sm text-blue-800 space-y-2">
            <p><strong>1. Search:</strong> Enter a topic in the search box and click Build Map (or press Enter)</p>
            <p><strong>2. Refine (optional):</strong> Narrow by discipline, date range, or source below</p>
            <p><strong>3. Interact:</strong> Click a paper node for an AI explanation; drag to pan, scroll to zoom</p>
            <p><strong>4. Reload:</strong> After changing filters, click Reload Map to refresh</p>
          </div>
        )}
      </div>

      {/* Enhanced Controls Panel */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Search & Filters</h2>

        {/* Primary search — drives vector retrieval for the map */}
        <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
          <label htmlFor="knowledge-map-search" className="block text-sm font-semibold text-gray-900 mb-2">
            Search the Knowledge Map
          </label>
          <p className="text-xs text-gray-600 mb-3">
            Describe a topic or question. We retrieve related papers and lay them out as an interactive graph.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              id="knowledge-map-search"
              type="text"
              value={keywordSearch}
              onChange={(e) => setKeywordSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  runUserSearch()
                }
              }}
              placeholder="e.g. nilpotent groups, CRISPR gene editing, mitochondrial respiration..."
              className="flex-1 px-4 py-3 text-sm border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              type="button"
              onClick={runUserSearch}
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              {loading ? 'Building…' : 'Build Map'}
            </button>
          </div>
          {keywordSearch.trim() && stats.nodes > 0 && !loading && (
            <p className="text-xs text-green-700 mt-2">
              Showing map for: <span className="font-medium">&ldquo;{keywordSearch.trim()}&rdquo;</span>
              {' '}({stats.papers} papers, {stats.concepts} concepts)
            </p>
          )}
        </div>
        
        {/* Quick Examples - curated to return results reliably */}
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">Quick Examples (Click to try)</h3>
          <p className="text-xs text-blue-700 mb-3">Try this pre-configured filter set that returns results:</p>
          
          <div className="mb-3">
            <p className="text-xs font-medium text-blue-800 mb-1">📐 Mathematics:</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => runQuickExample({
                  contentTypes: { papers: true, processes: false, videos: false, podcasts: false },
                  disciplines: { biology: false, chemistry: false, physics: false, mathematics: true, computer_science: false, interdisciplinary: false },
                  sources: { pubmed: false, arxiv: false, nasa_ads: false, crossref: false, youtube: false, rss: false },
                  dateRange: { start: '', end: '' },
                  keywordSearch: 'nilpotent group',
                  maxPapers: 10,
                })}
                className="text-xs px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Nilpotent Groups (Math)
              </button>
              <button
                onClick={() => runQuickExample({
                  contentTypes: { papers: true, processes: false, videos: false, podcasts: false },
                  disciplines: { biology: false, chemistry: false, physics: false, mathematics: true, computer_science: false, interdisciplinary: false },
                  sources: { pubmed: false, arxiv: false, nasa_ads: false, crossref: false, youtube: false, rss: false },
                  dateRange: { start: '', end: '' },
                  keywordSearch: 'spectral sequence',
                  maxPapers: 10,
                })}
                className="text-xs px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Spectral Sequences (Math)
              </button>
            </div>
          </div>

          <div className="mb-3">
            <p className="text-xs font-medium text-blue-800 mb-1">🧬 Biology:</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => runQuickExample({
                  contentTypes: { papers: true, processes: false, videos: false, podcasts: false },
                  disciplines: { biology: true, chemistry: false, physics: false, mathematics: false, computer_science: false, interdisciplinary: false },
                  sources: { pubmed: false, arxiv: false, nasa_ads: false, crossref: false, youtube: false, rss: false },
                  dateRange: { start: '', end: '' },
                  keywordSearch: 'aerobic respiration mitochondria',
                  maxPapers: 10,
                })}
                className="text-xs px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Aerobic Respiration (Biology)
              </button>
              <button
                onClick={() => runQuickExample({
                  contentTypes: { papers: true, processes: false, videos: false, podcasts: false },
                  disciplines: { biology: true, chemistry: false, physics: false, mathematics: false, computer_science: false, interdisciplinary: false },
                  sources: { pubmed: false, arxiv: false, nasa_ads: false, crossref: false, youtube: false, rss: false },
                  dateRange: { start: '', end: '' },
                  keywordSearch: 'glutamate acid resistance Escherichia coli',
                  maxPapers: 10,
                })}
                className="text-xs px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Acid Resistance (Biology)
              </button>
            </div>
          </div>
        </div>
        
        {/* Content Type Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Content Types to Visualize
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={contentTypes.papers}
                onChange={(e) => setContentTypes({ ...contentTypes, papers: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">📄 Papers</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={contentTypes.processes}
                onChange={(e) => setContentTypes({ ...contentTypes, processes: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">🔬 Processes</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={contentTypes.videos}
                onChange={(e) => setContentTypes({ ...contentTypes, videos: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">🎥 Videos</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={contentTypes.podcasts}
                onChange={(e) => setContentTypes({ ...contentTypes, podcasts: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">🎙️ Podcasts</span>
            </label>
          </div>
          <div className="mt-2 flex space-x-2">
            <button
              onClick={() => setContentTypes({ papers: true, processes: true, videos: true, podcasts: true })}
              className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              Select All
            </button>
            <button
              onClick={() => setContentTypes({ papers: false, processes: false, videos: false, podcasts: false })}
              className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              Deselect All
            </button>
          </div>
        </div>

        {/* Filters Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          {/* Discipline Filters */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Disciplines
            </label>
            <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-200 rounded p-2">
              {Object.entries(disciplines).map(([key, value]) => (
                <label key={key} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={(e) => setDisciplines({ ...disciplines, [key]: e.target.checked })}
                    className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-xs text-gray-700 capitalize">{key.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Source Filters */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sources
            </label>
            <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-200 rounded p-2">
              {Object.entries(sources).map(([key, value]) => (
                <label key={key} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={(e) => setSources({ ...sources, [key]: e.target.checked })}
                    className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-xs text-gray-700 uppercase">{key.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Date Range (optional)
            </label>
            <div className="space-y-2">
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Start date"
              />
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="End date"
              />
              <div className="flex space-x-1">
                <button
                  onClick={() => {
                    const end = new Date().toISOString().split('T')[0]
                    const start = new Date(new Date().setFullYear(new Date().getFullYear() - 1)).toISOString().split('T')[0]
                    setDateRange({ start, end })
                  }}
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Last Year
                </button>
                <button
                  onClick={() => {
                    const end = new Date().toISOString().split('T')[0]
                    const start = new Date(new Date().setFullYear(new Date().getFullYear() - 5)).toISOString().split('T')[0]
                    setDateRange({ start, end })
                  }}
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Last 5 Years
                </button>
                <button
                  onClick={() => setDateRange({ start: '', end: '' })}
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Visualization Customization */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4 border-t pt-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Papers
            </label>
            <input
              type="number"
              min="10"
              max="5000"
              value={maxPapers}
              onChange={(e) => setMaxPapers(parseInt(e.target.value) || 500)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Node Size By
            </label>
            <select
              value={nodeSizeBy}
              onChange={(e) => setNodeSizeBy(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="uniform">Uniform</option>
              <option value="citations">Citations</option>
              <option value="relevance">Relevance</option>
              <option value="date">Date</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Color By
            </label>
            <select
              value={colorBy}
              onChange={(e) => setColorBy(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="discipline">Discipline</option>
              <option value="content_type">Content Type</option>
              <option value="date">Date</option>
              <option value="source">Source</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Connections
            </label>
            <div className="space-y-1">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={includeConcepts}
                  onChange={(e) => setIncludeConcepts(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-xs text-gray-700">Concepts</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={includeSimilarity}
                  onChange={(e) => setIncludeSimilarity(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-xs text-gray-700">Similarity</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={includeCategories}
                  onChange={(e) => setIncludeCategories(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-xs text-gray-700">Categories</span>
              </label>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 border-t pt-4">
          <button
            onClick={() => {
              console.log('🔄 Reload Map clicked - loading with current filters...')
              loadKnowledgeMap()
            }}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? '⏳ Loading...' : '🔄 Reload Map'}
          </button>
          <button
            onClick={() => {
              console.log('🎯 Reset View clicked')
              resetView()
            }}
            disabled={!cyRef.current || loading}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            title="Center and fit the graph in the viewport"
          >
            🎯 Reset View
          </button>
          <button
            onClick={() => {
              console.log('✨ Clear Highlights clicked')
              clearHighlights()
            }}
            disabled={!cyRef.current || loading}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            title="Remove highlighting from all nodes"
          >
            ✨ Clear Highlights
          </button>
          <button
            onClick={() => {
              console.log('🔄 Reset Filters clicked - clearing all filters')
              setContentTypes({ papers: true, processes: false, videos: false, podcasts: false })
              setDisciplines({ biology: false, chemistry: false, physics: false, mathematics: false, computer_science: false, interdisciplinary: false })
              setSources({ pubmed: false, arxiv: false, nasa_ads: false, crossref: false, youtube: false, rss: false })
              setDateRange({ start: '', end: '' })
              setKeywordSearch('')
              setMaxPapers(10)
              // Clear the graph when filters are reset
              if (cyRef.current) {
                try {
                  cyRef.current.destroy()
                  cyRef.current = null
                  if (containerRef.current) {
                    containerRef.current.innerHTML = ''
                  }
                  setStats({ nodes: 0, edges: 0, papers: 0, concepts: 0 })
                } catch (err) {
                  console.debug('Error clearing graph on reset:', err)
                }
              }
            }}
            className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors"
            title="Reset all filters to defaults (clears the map - click Reload Map to refresh)"
          >
            🔄 Reset Filters
          </button>
        </div>
      </div>

      {/* Statistics + Node Explanation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{stats.nodes}</div>
              <div className="text-sm text-gray-600">Nodes</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{stats.edges}</div>
              <div className="text-sm text-gray-600">Edges</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{stats.papers}</div>
              <div className="text-sm text-gray-600">Papers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{stats.concepts}</div>
              <div className="text-sm text-gray-600">Concepts</div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            🧠 Node Explanation (OpenAI RAG)
          </h3>
          {!selectedNode && (
            <p className="text-xs text-gray-500">
              Click a paper or concept node in the graph to see an AI-generated explanation here.
            </p>
          )}
          {selectedNode && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">
                    {selectedNode.type === 'paper' ? 'Paper' : selectedNode.type === 'concept' ? 'Concept' : 'Node'}
                  </p>
                  <p className="text-sm font-medium text-gray-800">{selectedNode.label}</p>
                </div>
                <button
                  className="text-xs text-blue-600 hover:underline"
                  onClick={() => {
                    // Re-trigger explanation for current node
                    if (cyRef.current) {
                      const node = cyRef.current.getElementById(selectedNode.id)
                      if (node && node.length > 0) {
                        node.emit('tap') // reuse handler
                      }
                    }
                  }}
                >
                  Refresh Explanation
                </button>
              </div>
              {nodeExplanationLoading && (
                <p className="text-xs text-gray-500">Generating explanation...</p>
              )}
              {nodeExplanationError && (
                <p className="text-xs text-red-600">Error: {nodeExplanationError}</p>
              )}
              {nodeExplanation && (
                <div className="mt-1 max-h-40 overflow-y-auto text-xs text-gray-800 whitespace-pre-wrap border border-gray-100 rounded p-2 bg-gray-50">
                  {nodeExplanation}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Knowledge Map Visualization */}
      <div className="bg-white rounded-lg shadow p-6">
        {/* Wrapper div that React manages - contains overlay UI */}
        <div className="w-full h-[600px] border border-gray-200 rounded-md relative" style={{ minHeight: '600px' }}>
          {/* Cytoscape container - stable reference, no key to prevent remounting */}
          <div
            ref={containerRef}
            className="absolute inset-0 w-full h-full z-0"
            style={{ width: '100%', height: '100%' }}
            suppressHydrationWarning
            suppressContentEditableWarning
          />
          
          {/* Overlay UI - managed by React, positioned above Cytoscape */}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-20 pointer-events-none">
              <div className="text-center pointer-events-auto">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading knowledge map...</p>
                <p className="text-xs text-gray-500 mt-2">Fetching from: {API_BASE_URL}/api/knowledge-map/graph</p>
                <p className="text-xs text-gray-400 mt-1">Check browser console (F12) for details</p>
              </div>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-20 pointer-events-none">
              <div className="bg-red-50 border border-red-200 rounded-md p-4 max-w-md pointer-events-auto">
                <p className="text-red-800 font-semibold">Error: {error}</p>
                <p className="text-sm text-red-600 mt-2">
                  Make sure the API server is running at {API_BASE_URL}
                </p>
                <button
                  onClick={() => {
                    setError(null)
                    loadKnowledgeMap()
                  }}
                  className="mt-3 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm"
                >
                  Retry
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Legend</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
            <span>Papers</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-500 transform rotate-45" style={{ width: '16px', height: '16px' }}></div>
            <span>Concepts</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-400"></div>
            <span>Similarity</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500"></div>
            <span>Category</span>
          </div>
        </div>
      </div>
    </div>
  )
}

