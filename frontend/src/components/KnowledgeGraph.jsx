import { useState, useEffect, useRef, useCallback } from 'react';

const API = 'http://127.0.0.1:8000';
const TYPE_COLORS = { borrower: '#00e68a', employer: '#3b82f6', community: '#a855f7', merchant: '#f59e0b', assessment: '#f43f5e', income_source: '#ec4899' };
const TYPE_RADIUS = { borrower: 10, employer: 14, community: 14, merchant: 8, assessment: 6, income_source: 8 };

export default function KnowledgeGraphPage() {
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [stats, setStats] = useState({});
  const [insights, setInsights] = useState([]);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState(null);
  const svgRef = useRef(null);
  const simRef = useRef(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/kg/graph`).then(r => r.json()).catch(() => ({ nodes: [], links: [] })),
      fetch(`${API}/kg/stats`).then(r => r.json()).catch(() => ({})),
      fetch(`${API}/kg/insights`).then(r => r.json()).catch(() => ({ insights: [] })),
    ]).then(([g, s, ins]) => {
      setGraph(g);
      setStats(s);
      setInsights(ins.insights || []);
    }).catch(e => setError(e.message));
  }, []);

  // Simple force simulation
  const [positions, setPositions] = useState([]);
  useEffect(() => {
    if (!graph.nodes?.length) return;
    const W = 700, H = 500;
    const nodes = graph.nodes.map((n, i) => ({
      ...n, x: W / 2 + (Math.random() - 0.5) * 300, y: H / 2 + (Math.random() - 0.5) * 200, vx: 0, vy: 0,
    }));
    const nodeMap = {};
    nodes.forEach((n, i) => { nodeMap[n.id] = i; });
    const links = (graph.links || []).filter(l => nodeMap[l.source] !== undefined && nodeMap[l.target] !== undefined);

    let frame;
    const tick = () => {
      // Center gravity
      nodes.forEach(n => { n.vx += (W / 2 - n.x) * 0.001; n.vy += (H / 2 - n.y) * 0.001; });
      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = 800 / (d * d);
          nodes[i].vx -= dx / d * f; nodes[i].vy -= dy / d * f;
          nodes[j].vx += dx / d * f; nodes[j].vy += dy / d * f;
        }
      }
      // Attraction along edges
      links.forEach(l => {
        const si = nodeMap[l.source], ti = nodeMap[l.target];
        if (si === undefined || ti === undefined) return;
        const dx = nodes[ti].x - nodes[si].x, dy = nodes[ti].y - nodes[si].y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (d - 80) * 0.01;
        nodes[si].vx += dx / d * f; nodes[si].vy += dy / d * f;
        nodes[ti].vx -= dx / d * f; nodes[ti].vy -= dy / d * f;
      });
      // Damping + position update
      nodes.forEach(n => {
        n.vx *= 0.85; n.vy *= 0.85;
        n.x = Math.max(30, Math.min(W - 30, n.x + n.vx));
        n.y = Math.max(30, Math.min(H - 30, n.y + n.vy));
      });
      setPositions([...nodes]);
    };

    let i = 0;
    const loop = () => { tick(); i++; if (i < 150) frame = requestAnimationFrame(loop); };
    frame = requestAnimationFrame(loop);
    simRef.current = { nodes, links, nodeMap };
    return () => cancelAnimationFrame(frame);
  }, [graph]);

  const visibleNodes = positions.filter(n => filter === 'all' || n.type === filter);
  const visibleIds = new Set(visibleNodes.map(n => n.id));
  const sim = simRef.current;
  const visibleLinks = sim ? sim.links.filter(l => visibleIds.has(l.source) && visibleIds.has(l.target)) : [];
  const nodeTypes = [...new Set(graph.nodes?.map(n => n.type) || [])];

  const getPos = (id) => positions.find(p => p.id === id) || { x: 0, y: 0 };

  return (
    <div className="kg-page">
      {error && <div className="card" style={{ borderColor: '#f43f5e', color: '#f43f5e', marginBottom: 16 }}>Error: {error}</div>}

      <div className="kg-stats-row animate-in">
        {[
          { label: 'Nodes', value: stats.total_nodes || 0 },
          { label: 'Edges', value: stats.total_edges || 0 },
          { label: 'Borrowers', value: stats.node_types?.borrower || 0 },
          { label: 'Employers', value: stats.node_types?.employer || 0 },
          { label: 'Communities', value: stats.node_types?.community || 0 },
          { label: 'Density', value: stats.density?.toFixed(3) || '—' },
        ].map((m, i) => (
          <div className="card-metric" key={i}>
            <span className="metric-label">{m.label}</span>
            <span className="metric-value" style={{ fontSize: '1.4rem' }}>{m.value}</span>
          </div>
        ))}
      </div>

      <div className="kg-canvas animate-in-1" style={{ position: 'relative' }}>
        <div className="kg-controls">
          <select className="persona-select" style={{ width: 'auto', fontSize: '0.8rem', padding: '4px 10px' }} value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="all">All Types</option>
            {nodeTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {Object.entries(TYPE_COLORS).filter(([t]) => nodeTypes.includes(t)).map(([t, c]) => (
              <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', color: 'var(--text-1)' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} /> {t}
              </span>
            ))}
          </div>
        </div>
        <svg ref={svgRef} width="100%" height="500" viewBox="0 0 700 500" style={{ background: 'var(--bg-1)' }}>
          <defs><marker id="arrow" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.15)" /></marker></defs>
          {visibleLinks.map((l, i) => {
            const s = getPos(l.source), t = getPos(l.target);
            return <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="rgba(255,255,255,0.1)" strokeWidth={1} markerEnd="url(#arrow)" strokeDasharray={l.type === 'similar_to' ? '4 4' : 'none'} />;
          })}
          {visibleNodes.map(n => (
            <g key={n.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(n)}>
              <circle cx={n.x} cy={n.y} r={TYPE_RADIUS[n.type] || 8} fill={TYPE_COLORS[n.type] || '#666'} opacity={0.85} stroke={selected?.id === n.id ? '#fff' : 'transparent'} strokeWidth={2} />
              <text x={n.x} y={n.y + (TYPE_RADIUS[n.type] || 8) + 12} textAnchor="middle" fill="var(--text-1)" fontSize="9" fontFamily="var(--font)">{(n.name || n.id).slice(0, 14)}</text>
            </g>
          ))}
        </svg>

        {selected && (
          <div className="kg-detail-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>{selected.name || selected.id}</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div><span style={{ color: 'var(--text-1)', fontSize: '0.78rem' }}>Type</span><div><span className={`badge badge-${selected.type === 'borrower' ? 'success' : 'info'}`}>{selected.type}</span></div></div>
              <div><span style={{ color: 'var(--text-1)', fontSize: '0.78rem' }}>ID</span><div style={{ fontSize: '0.82rem', fontFamily: 'monospace' }}>{selected.id}</div></div>
              {selected.score && <div><span style={{ color: 'var(--text-1)', fontSize: '0.78rem' }}>Score</span><div style={{ fontWeight: 700, color: selected.score >= 700 ? '#00e68a' : '#f59e0b' }}>{selected.score}</div></div>}
              {selected.decision && <div><span style={{ color: 'var(--text-1)', fontSize: '0.78rem' }}>Decision</span><div>{selected.decision}</div></div>}
              {selected.risk_tier && <div><span style={{ color: 'var(--text-1)', fontSize: '0.78rem' }}>Risk Tier</span><div>{selected.risk_tier}</div></div>}
            </div>
          </div>
        )}
      </div>

      {insights.length > 0 && (
        <div className="card animate-in-2" style={{ marginTop: 16 }}>
          <div className="section-title">🧠 Graph Insights</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {insights.map((ins, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                <span className={`badge badge-${ins.severity === 'high' ? 'danger' : ins.severity === 'medium' ? 'warning' : 'info'}`}>{ins.type}</span>
                <div><div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{ins.title}</div><div style={{ fontSize: '0.8rem', color: 'var(--text-1)' }}>{ins.description}</div></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
