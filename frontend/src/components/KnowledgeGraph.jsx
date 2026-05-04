import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, Filter, ZoomIn, ZoomOut, Maximize2, Info, Brain, TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react';

const API = 'http://127.0.0.1:8000';
const TYPE_COLORS = { borrower: '#00FF9D', employer: '#3B82F6', community: '#A855F7', merchant: '#F59E0B', assessment: '#6366F1', income_source: '#EC4899' };
const RISK_COLORS = { High: '#FF3B30', Medium: '#F59E0B', Low: '#00FF9D' };
const EDGE_COLORS = { works_at: '#3B82F6', lives_in: '#A855F7', referred_by: '#F59E0B', pays_utility: '#EC4899', similar_to: '#6366F1', assessed_on: '#6366F180' };

function useGraphSimulation(nodes, edges, width, height) {
  const [positions, setPositions] = useState({});
  const simRef = useRef(null);
  useEffect(() => {
    if (!nodes.length) return;
    const pos = {};
    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      const r = Math.min(width, height) * 0.35;
      pos[n.id] = { x: width/2 + r * Math.cos(angle) + (Math.random()-0.5)*40, y: height/2 + r * Math.sin(angle) + (Math.random()-0.5)*40, vx: 0, vy: 0 };
    });
    const edgeMap = edges.map(e => ({ s: e.source, t: e.target }));
    let frame;
    const tick = () => {
      const alpha = 0.3;
      nodes.forEach(n => { // center gravity
        const p = pos[n.id]; if(!p) return;
        p.vx += (width/2 - p.x) * 0.001; p.vy += (height/2 - p.y) * 0.001;
      });
      nodes.forEach((a, i) => { // repulsion
        nodes.forEach((b, j) => {
          if (i >= j) return; const pa = pos[a.id], pb = pos[b.id]; if(!pa||!pb) return;
          let dx = pa.x - pb.x, dy = pa.y - pb.y, d = Math.sqrt(dx*dx+dy*dy) || 1;
          if (d < 200) { const f = 800 / (d*d); pa.vx += dx/d*f; pa.vy += dy/d*f; pb.vx -= dx/d*f; pb.vy -= dy/d*f; }
        });
      });
      edgeMap.forEach(e => { // attraction
        const pa = pos[e.s], pb = pos[e.t]; if(!pa||!pb) return;
        let dx = pb.x-pa.x, dy = pb.y-pa.y, d = Math.sqrt(dx*dx+dy*dy)||1;
        const f = (d - 100) * 0.005;
        pa.vx += dx/d*f; pa.vy += dy/d*f; pb.vx -= dx/d*f; pb.vy -= dy/d*f;
      });
      let moving = false;
      nodes.forEach(n => {
        const p = pos[n.id]; if(!p) return;
        p.vx *= 0.85; p.vy *= 0.85;
        p.x += p.vx; p.y += p.vy;
        p.x = Math.max(30, Math.min(width-30, p.x)); p.y = Math.max(30, Math.min(height-30, p.y));
        if (Math.abs(p.vx) > 0.1 || Math.abs(p.vy) > 0.1) moving = true;
      });
      setPositions({...pos});
      if (moving) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    simRef.current = { pos, stop: () => cancelAnimationFrame(frame) };
    return () => cancelAnimationFrame(frame);
  }, [nodes.length, edges.length, width, height]);
  return [positions, simRef];
}

export default function KnowledgeGraphPage() {
  const navigate = useNavigate();
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], stats: {} });
  const [insights, setInsights] = useState({ insights: [], threshold_suggestion: {} });
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [selected, setSelected] = useState(null);
  const [nodeDetail, setNodeDetail] = useState(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [zoom, setZoom] = useState(1);
  const canvasW = 900, canvasH = 550;

  const loadData = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API}/kg/graph`).then(r=>r.json()).catch(()=>({nodes:[],edges:[],stats:{}})),
      fetch(`${API}/kg/insights`).then(r=>r.json()).catch(()=>({insights:[],threshold_suggestion:{}})),
    ]).then(([g,i]) => { setGraphData(g); setInsights(i); setLoading(false); });
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const seedKG = async () => {
    setSeeding(true);
    try { await fetch(`${API}/kg/seed`, {method:'POST'}); await new Promise(r=>setTimeout(r,500)); loadData(); }
    catch(e) { console.error(e); }
    setSeeding(false);
  };

  const filteredNodes = graphData.nodes.filter(n => {
    if (filterType !== 'all' && n.type !== filterType) return false;
    if (search && !n.name?.toLowerCase().includes(search.toLowerCase()) && !n.id?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });
  const nodeIds = new Set(filteredNodes.map(n=>n.id));
  const filteredEdges = graphData.edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));

  const [positions] = useGraphSimulation(filteredNodes, filteredEdges, canvasW, canvasH);

  const selectNode = async (node) => {
    setSelected(node);
    try {
      const r = await fetch(`${API}/kg/node/${node.id}`);
      const d = await r.json();
      setNodeDetail(d);
    } catch(e) { setNodeDetail(null); }
  };

  const stats = graphData.stats || {};
  const sevColors = { high: '#FF3B30', medium: '#F59E0B', low: '#00FF9D', info: '#3B82F6' };

  return (
    <div style={{ padding: '2rem', maxWidth: '1500px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'2rem' }}>
        <div>
          <button onClick={()=>navigate('/')} style={{ background:'none', border:'none', color:'var(--text-muted)', cursor:'pointer', display:'flex', alignItems:'center', gap:'8px', marginBottom:'0.8rem', fontFamily:'Inter', fontSize:'0.9rem' }}>
            <ArrowLeft size={16}/> Back to Home
          </button>
          <h1 style={{ fontFamily:'Outfit', fontSize:'2.5rem', fontWeight:800, letterSpacing:'-1px' }}>
            <span style={{color:'var(--neon-mint)'}}>Knowledge</span> Graph
          </h1>
          <p style={{color:'var(--text-muted)'}}>Dynamic, self-growing credit intelligence network</p>
        </div>
        <div style={{display:'flex', gap:'1rem'}}>
          <button className="btn-outline" onClick={loadData} style={{width:'auto',padding:'0.6rem 1.2rem',fontSize:'0.85rem'}}><RefreshCw size={14}/> Refresh</button>
          <button className="btn-primary" onClick={seedKG} disabled={seeding} style={{width:'auto',padding:'0.6rem 1.2rem',fontSize:'0.85rem'}}>
            {seeding ? 'Seeding...' : '⚡ Seed Graph'}
          </button>
        </div>
      </div>

      {loading ? (
        <p className="pulse-text" style={{textAlign:'center',padding:'4rem'}}>Loading knowledge graph...</p>
      ) : (
        <>
          {/* Stats Bar */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(6,1fr)', gap:'1rem', marginBottom:'2rem' }}>
            {[
              ['Nodes', stats.total_nodes||0, 'var(--neon-mint)'],
              ['Edges', stats.total_edges||0, 'var(--neon-mint)'],
              ['Borrowers', stats.borrower_count||0, '#3B82F6'],
              ['Avg Degree', stats.avg_degree||0, '#A855F7'],
              ['Density', stats.density||0, '#F59E0B'],
              ['Components', stats.connected_components||0, '#EC4899'],
            ].map(([label, val, color]) => (
              <div key={label} className="glass-card-cred" style={{padding:'1.2rem',textAlign:'center'}}>
                <div style={{fontFamily:'Outfit',fontSize:'1.8rem',fontWeight:800,color}}>{val}</div>
                <div style={{color:'var(--text-muted)',fontSize:'0.7rem',letterSpacing:'2px',textTransform:'uppercase',marginTop:'0.3rem'}}>{label}</div>
              </div>
            ))}
          </div>

          {/* Main Content: Graph + Panel */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 380px', gap:'1.5rem', marginBottom:'2rem' }}>
            {/* Graph Canvas */}
            <div className="glass-card-cred" style={{padding:'1.5rem', position:'relative', overflow:'hidden'}}>
              {/* Controls */}
              <div style={{display:'flex',gap:'0.8rem',marginBottom:'1rem',alignItems:'center',flexWrap:'wrap'}}>
                <div style={{position:'relative',flex:1,minWidth:'180px'}}>
                  <Search size={14} style={{position:'absolute',left:'12px',top:'50%',transform:'translateY(-50%)',color:'var(--text-muted)'}}/>
                  <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search nodes..." style={{width:'100%',padding:'0.6rem 0.6rem 0.6rem 2.2rem',borderRadius:'10px',background:'var(--bg-darker)',border:'1px solid var(--border-subtle)',color:'var(--text-primary)',fontFamily:'Inter',fontSize:'0.85rem',outline:'none'}}/>
                </div>
                <select value={filterType} onChange={e=>setFilterType(e.target.value)} style={{padding:'0.6rem 1rem',borderRadius:'10px',background:'var(--bg-darker)',border:'1px solid var(--border-subtle)',color:'var(--text-primary)',fontFamily:'Inter',fontSize:'0.85rem',outline:'none'}}>
                  <option value="all">All Types</option>
                  <option value="borrower">Borrowers</option>
                  <option value="employer">Employers</option>
                  <option value="community">Communities</option>
                  <option value="merchant">Merchants</option>
                </select>
                <div style={{display:'flex',gap:'4px'}}>
                  <button onClick={()=>setZoom(z=>Math.min(z+0.2,3))} style={{background:'var(--bg-darker)',border:'1px solid var(--border-subtle)',borderRadius:'8px',padding:'0.4rem',cursor:'pointer',color:'var(--text-muted)'}}><ZoomIn size={14}/></button>
                  <button onClick={()=>setZoom(z=>Math.max(z-0.2,0.3))} style={{background:'var(--bg-darker)',border:'1px solid var(--border-subtle)',borderRadius:'8px',padding:'0.4rem',cursor:'pointer',color:'var(--text-muted)'}}><ZoomOut size={14}/></button>
                  <button onClick={()=>setZoom(1)} style={{background:'var(--bg-darker)',border:'1px solid var(--border-subtle)',borderRadius:'8px',padding:'0.4rem',cursor:'pointer',color:'var(--text-muted)'}}><Maximize2 size={14}/></button>
                </div>
              </div>

              {/* SVG Graph */}
              <div style={{overflow:'hidden',borderRadius:'12px',background:'rgba(0,0,0,0.3)',border:'1px solid var(--border-subtle)'}}>
                <svg width={canvasW} height={canvasH} viewBox={`0 0 ${canvasW} ${canvasH}`} style={{display:'block',transform:`scale(${zoom})`,transformOrigin:'center',transition:'transform 0.2s'}}>
                  <defs>
                    <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
                  </defs>
                  {/* Edges */}
                  {filteredEdges.map((e,i) => {
                    const ps = positions[e.source], pt = positions[e.target];
                    if(!ps||!pt) return null;
                    return <line key={i} x1={ps.x} y1={ps.y} x2={pt.x} y2={pt.y} stroke={EDGE_COLORS[e.type]||'#444'} strokeWidth={e.type==='similar_to'?1:1.5} strokeDasharray={e.type==='similar_to'?'4,4':''} opacity={0.5}/>;
                  })}
                  {/* Nodes */}
                  {filteredNodes.map(n => {
                    const p = positions[n.id]; if(!p) return null;
                    const color = n.type==='borrower' ? (RISK_COLORS[n.risk_tier]||n.color) : (TYPE_COLORS[n.type]||'#888');
                    const r = (n.size||8) * (selected?.id===n.id ? 1.5 : 1);
                    const isSelected = selected?.id===n.id;
                    return (
                      <g key={n.id} onClick={()=>selectNode(n)} style={{cursor:'pointer'}}>
                        <circle cx={p.x} cy={p.y} r={r+4} fill="transparent"/>
                        <circle cx={p.x} cy={p.y} r={r} fill={color} opacity={isSelected?1:0.85} filter={isSelected?'url(#glow)':''} stroke={isSelected?'#fff':'none'} strokeWidth={isSelected?2:0}/>
                        <text x={p.x} y={p.y+(r+12)} textAnchor="middle" fill="var(--text-muted)" fontSize="9" fontFamily="Inter">{n.name?.length>12?n.name.slice(0,12)+'…':n.name}</text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Legend */}
              <div style={{display:'flex',gap:'1.2rem',marginTop:'0.8rem',flexWrap:'wrap',fontSize:'0.75rem'}}>
                {Object.entries(TYPE_COLORS).map(([t,c]) => (
                  <span key={t} style={{display:'flex',alignItems:'center',gap:'4px',color:'var(--text-muted)'}}>
                    <span style={{width:10,height:10,borderRadius:'50%',background:c,display:'inline-block'}}/>{t}
                  </span>
                ))}
              </div>
            </div>

            {/* Side Panel */}
            <div style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
              {/* Node Detail */}
              <div className="glass-card-cred" style={{padding:'1.5rem',flex:1,overflowY:'auto',maxHeight:'620px'}}>
                {!selected ? (
                  <div style={{textAlign:'center',color:'var(--text-muted)',padding:'3rem 1rem'}}>
                    <Info size={32} style={{marginBottom:'1rem',opacity:0.5}}/>
                    <p style={{fontSize:'0.9rem'}}>Click a node to inspect</p>
                    <p style={{fontSize:'0.8rem',marginTop:'0.5rem'}}>{filteredNodes.length} nodes • {filteredEdges.length} edges</p>
                  </div>
                ) : (
                  <>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'start',marginBottom:'1rem'}}>
                      <div>
                        <h3 style={{fontFamily:'Outfit',fontSize:'1.2rem',fontWeight:700}}>{selected.name}</h3>
                        <span style={{fontSize:'0.75rem',padding:'0.15rem 0.6rem',borderRadius:'50px',background:(TYPE_COLORS[selected.type]||'#888')+'22',color:TYPE_COLORS[selected.type]||'#888',fontWeight:600}}>{selected.type}</span>
                      </div>
                      <button onClick={()=>{setSelected(null);setNodeDetail(null)}} style={{background:'none',border:'none',color:'var(--text-muted)',cursor:'pointer',fontSize:'1.2rem'}}>×</button>
                    </div>

                    {selected.type==='borrower' && selected.score && (
                      <div style={{background:'rgba(0,255,157,0.05)',border:'1px solid rgba(0,255,157,0.15)',borderRadius:'12px',padding:'1rem',marginBottom:'1rem'}}>
                        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                          <span style={{color:'var(--text-muted)',fontSize:'0.8rem'}}>Credit Score</span>
                          <span style={{fontFamily:'Outfit',fontSize:'1.8rem',fontWeight:800,color:RISK_COLORS[selected.risk_tier]||'var(--neon-mint)'}}>{selected.score}</span>
                        </div>
                        <div style={{display:'flex',gap:'0.8rem',marginTop:'0.5rem'}}>
                          <span style={{fontSize:'0.75rem',padding:'0.15rem 0.5rem',borderRadius:'50px',background:(RISK_COLORS[selected.risk_tier]||'#888')+'22',color:RISK_COLORS[selected.risk_tier]||'#888'}}>{selected.risk_tier}</span>
                          <span style={{fontSize:'0.75rem',color:'var(--text-muted)'}}>{selected.decision}</span>
                        </div>
                      </div>
                    )}

                    {selected.features && Object.keys(selected.features).length > 0 && (
                      <div style={{marginBottom:'1rem'}}>
                        <h4 style={{fontSize:'0.75rem',color:'var(--text-muted)',letterSpacing:'1px',textTransform:'uppercase',marginBottom:'0.5rem'}}>Features</h4>
                        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0.3rem'}}>
                          {Object.entries(selected.features).map(([k,v])=>(
                            <div key={k} style={{fontSize:'0.8rem'}}><span style={{color:'var(--text-muted)'}}>{k}:</span> <strong>{typeof v==='number'?v.toFixed(2):v}</strong></div>
                          ))}
                        </div>
                      </div>
                    )}

                    {nodeDetail?.graph_features && (
                      <div style={{marginBottom:'1rem'}}>
                        <h4 style={{fontSize:'0.75rem',color:'var(--text-muted)',letterSpacing:'1px',textTransform:'uppercase',marginBottom:'0.5rem'}}>Graph Context</h4>
                        <div style={{fontSize:'0.8rem',display:'flex',flexDirection:'column',gap:'0.3rem'}}>
                          <div><span style={{color:'var(--text-muted)'}}>Employer:</span> {nodeDetail.graph_features.employer_name}</div>
                          <div><span style={{color:'var(--text-muted)'}}>Community:</span> {nodeDetail.graph_features.community_name}</div>
                          <div><span style={{color:'var(--text-muted)'}}>Degree:</span> {nodeDetail.graph_features.graph_degree}</div>
                          <div><span style={{color:'var(--text-muted)'}}>Adjustment:</span> <strong style={{color:nodeDetail.graph_features.graph_risk_adjustment>=0?'var(--neon-mint)':'var(--danger)'}}>{nodeDetail.graph_features.graph_risk_adjustment>=0?'+':''}{nodeDetail.graph_features.graph_risk_adjustment} pts</strong></div>
                          {nodeDetail.graph_features.referral_bonus && <div style={{color:'var(--neon-mint)'}}>✓ Referral Bonus</div>}
                        </div>
                        {nodeDetail.graph_features.graph_notes && <p style={{fontSize:'0.75rem',color:'var(--text-muted)',marginTop:'0.5rem',fontStyle:'italic'}}>{nodeDetail.graph_features.graph_notes}</p>}
                      </div>
                    )}

                    {nodeDetail?.edges && nodeDetail.edges.length > 0 && (
                      <div>
                        <h4 style={{fontSize:'0.75rem',color:'var(--text-muted)',letterSpacing:'1px',textTransform:'uppercase',marginBottom:'0.5rem'}}>Connections ({nodeDetail.edges.length})</h4>
                        {nodeDetail.edges.slice(0,10).map((e,i)=>(
                          <div key={i} style={{fontSize:'0.8rem',padding:'0.3rem 0',borderBottom:'1px solid var(--border-subtle)',display:'flex',justifyContent:'space-between'}}>
                            <span style={{color:EDGE_COLORS[e.type]||'#888'}}>{e.type}</span>
                            <span style={{color:'var(--text-muted)'}}>{e.source_id===selected.id?e.target_id:e.source_id}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {selected.type==='employer' && (<div style={{fontSize:'0.8rem',marginTop:'0.5rem'}}><span style={{color:'var(--text-muted)'}}>Sector:</span> {selected.sector} | <span style={{color:'var(--text-muted)'}}>Default Rate:</span> {((selected.default_rate||0.05)*100).toFixed(0)}%</div>)}
                    {selected.type==='community' && (<div style={{fontSize:'0.8rem',marginTop:'0.5rem'}}><span style={{color:'var(--text-muted)'}}>Repayment Rate:</span> {((selected.repayment_rate||0.80)*100).toFixed(0)}%</div>)}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Insights Section */}
          {insights.insights && insights.insights.length > 0 && (
            <div className="glass-card-cred" style={{padding:'2rem',marginBottom:'2rem'}}>
              <h3 style={{fontFamily:'Outfit',fontSize:'1.3rem',fontWeight:700,marginBottom:'1.5rem',display:'flex',alignItems:'center',gap:'10px'}}>
                <Brain size={20} color="var(--neon-mint)"/> Self-Improving Insights
              </h3>
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(320px,1fr))',gap:'1rem'}}>
                {insights.insights.map((ins,i) => (
                  <div key={i} style={{background:'rgba(255,255,255,0.02)',border:`1px solid ${(sevColors[ins.severity]||'#555')}33`,borderRadius:'14px',padding:'1.2rem'}}>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'start',marginBottom:'0.5rem'}}>
                      <h4 style={{fontSize:'0.9rem',fontWeight:600,flex:1}}>{ins.title}</h4>
                      <span style={{fontSize:'0.65rem',padding:'0.1rem 0.5rem',borderRadius:'50px',background:(sevColors[ins.severity]||'#555')+'22',color:sevColors[ins.severity]||'#555',fontWeight:600,whiteSpace:'nowrap'}}>{ins.severity}</span>
                    </div>
                    <p style={{fontSize:'0.8rem',color:'var(--text-muted)',lineHeight:1.5}}>{ins.description}</p>
                  </div>
                ))}
              </div>

              {/* Threshold Suggestion */}
              {insights.threshold_suggestion && insights.threshold_suggestion.suggestion !== 'none' && (
                <div style={{marginTop:'1.5rem',background:'rgba(0,255,157,0.05)',border:'1px solid rgba(0,255,157,0.15)',borderRadius:'14px',padding:'1.2rem'}}>
                  <h4 style={{fontSize:'0.85rem',fontWeight:600,display:'flex',alignItems:'center',gap:'8px',marginBottom:'0.5rem'}}>
                    <TrendingUp size={16} color="var(--neon-mint)"/> Threshold Recommendation
                  </h4>
                  <p style={{fontSize:'0.8rem',color:'var(--text-muted)'}}>{insights.threshold_suggestion.reason}</p>
                  <div style={{display:'flex',gap:'2rem',marginTop:'0.8rem',fontSize:'0.8rem'}}>
                    <div><span style={{color:'var(--text-muted)'}}>Current:</span> DECLINE &lt; {insights.threshold_suggestion.current_thresholds?.DECLINE_UPPER}</div>
                    <div><span style={{color:'var(--neon-mint)'}}>Suggested:</span> DECLINE &lt; {insights.threshold_suggestion.suggested_thresholds?.DECLINE_UPPER}</div>
                    <div><span style={{color:'var(--text-muted)'}}>Based on:</span> {insights.threshold_suggestion.borrower_count} borrowers</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Node Types Legend */}
          <div className="glass-card-cred" style={{padding:'1.5rem'}}>
            <h4 style={{fontFamily:'Outfit',fontSize:'1rem',fontWeight:600,marginBottom:'1rem'}}>Node Types in Graph</h4>
            <div style={{display:'flex',gap:'2rem',flexWrap:'wrap'}}>
              {Object.entries(stats.node_types||{}).map(([t,c])=>(
                <div key={t} style={{display:'flex',alignItems:'center',gap:'8px'}}>
                  <span style={{width:14,height:14,borderRadius:'50%',background:TYPE_COLORS[t]||'#888'}}/>
                  <span style={{fontSize:'0.85rem',textTransform:'capitalize'}}>{t}</span>
                  <span style={{fontSize:'0.8rem',color:'var(--text-muted)'}}>({c})</span>
                </div>
              ))}
              {Object.entries(stats.edge_types||{}).map(([t,c])=>(
                <div key={t} style={{display:'flex',alignItems:'center',gap:'8px'}}>
                  <span style={{width:14,height:3,background:EDGE_COLORS[t]||'#555',borderRadius:2}}/>
                  <span style={{fontSize:'0.85rem'}}>{t}</span>
                  <span style={{fontSize:'0.8rem',color:'var(--text-muted)'}}>({c})</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
