import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { ArrowLeft, Users, TrendingUp, ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, BrainCircuit, Network } from 'lucide-react';

const RISK_COLORS = { High: '#FF3B30', Medium: '#F59E0B', Low: '#00FF9D' };
const DECISION_COLORS = { STANDARD: '#00FF9D', NANO_CREDIT: '#F59E0B', DECLINE: '#FF3B30' };

export default function Dashboard() {
  const navigate = useNavigate();
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [llmStats, setLlmStats] = useState(null);
  const [llmSessions, setLlmSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [kgStats, setKgStats] = useState(null);
  const [kgInsights, setKgInsights] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch('http://127.0.0.1:8000/applications-log').then(r => r.json()),
      fetch('http://127.0.0.1:8000/sessions-summary').then(r => r.json()).catch(() => null),
      fetch('http://127.0.0.1:8000/completed-sessions').then(r => r.json()).catch(() => ({sessions:[]})),
      fetch('http://127.0.0.1:8000/kg/stats').then(r => r.json()).catch(() => null),
      fetch('http://127.0.0.1:8000/kg/insights').then(r => r.json()).catch(() => null),
    ]).then(([logData, statsData, sessData, kgData, kgIns]) => {
      setApps(logData.applications || []);
      if (statsData) setLlmStats(statsData);
      setLlmSessions(sessData.sessions || []);
      if (kgData) setKgStats(kgData);
      if (kgIns) setKgInsights(kgIns);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const openSessionDetail = async (sessionId) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/session/${sessionId}`);
      const data = await res.json();
      setSessionDetail(data);
      setSelectedSession(sessionId);
    } catch (e) { console.error(e); }
  };

  // Computed metrics
  const totalApps = apps.length;
  const avgScore = totalApps ? Math.round(apps.reduce((s, a) => s + (a.score || 0), 0) / totalApps) : 0;
  const approvalRate = totalApps ? Math.round(apps.filter(a => a.decision !== 'DECLINE').length / totalApps * 100) : 0;
  const avgILF = totalApps ? (apps.reduce((s, a) => s + (a.ilf_reliability || 0), 0) / totalApps) : 0;
  const flaggedCount = apps.filter(a => a.catch_trial_flagged).length;

  // Distribution data
  const riskCounts = { High: 0, Medium: 0, Low: 0 };
  const decisionCounts = { STANDARD: 0, NANO_CREDIT: 0, DECLINE: 0 };
  apps.forEach(a => {
    if (a.risk_tier) riskCounts[a.risk_tier] = (riskCounts[a.risk_tier] || 0) + 1;
    if (a.decision) decisionCounts[a.decision] = (decisionCounts[a.decision] || 0) + 1;
  });

  const riskData = Object.entries(riskCounts).map(([name, value]) => ({ name, value }));
  const decisionData = Object.entries(decisionCounts).map(([name, value]) => ({ name, value }));

  // Score distribution for histogram
  const scoreBuckets = {};
  apps.forEach(a => {
    const bucket = Math.floor((a.score || 300) / 50) * 50;
    scoreBuckets[bucket] = (scoreBuckets[bucket] || 0) + 1;
  });
  const scoreHistData = Object.entries(scoreBuckets).sort((a,b) => +a[0] - +b[0]).map(([range, count]) => ({ range: `${range}-${+range+49}`, count }));

  const kpiStyle = { textAlign: 'center', padding: '2rem' };
  const kpiValue = (v, color='var(--neon-mint)') => ({ fontFamily: 'Outfit', fontSize: '3rem', fontWeight: 900, color, lineHeight: 1 });
  const kpiLabel = { color: 'var(--text-muted)', fontSize: '0.8rem', letterSpacing: '2px', textTransform: 'uppercase', marginTop: '0.8rem' };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
        <div>
          <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem', fontFamily: 'Inter', fontSize: '0.9rem' }}>
            <ArrowLeft size={16}/> Back to Home
          </button>
          <h1 style={{ fontFamily: 'Outfit', fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-1px' }}>
            <span style={{ color: 'var(--neon-mint)' }}>Bank</span> Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>Real-time portfolio analytics and risk monitoring</p>
        </div>
        <div style={{ display: 'flex', gap: '0.8rem' }}>
          <button className="btn-outline" onClick={() => navigate('/knowledge-graph')} style={{ width: 'auto', padding: '0.8rem 1.2rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Network size={16}/> Knowledge Graph
          </button>
          <button className="btn-primary" onClick={() => navigate('/assess')} style={{ width: 'auto', padding: '0.8rem 1.5rem', fontSize: '0.9rem' }}>
            + New Assessment
          </button>
        </div>
      </div>

      {loading ? (
        <p className="pulse-text" style={{ textAlign: 'center', padding: '4rem' }}>Loading analytics...</p>
      ) : totalApps === 0 ? (
        <div className="glass-card-cred" style={{ textAlign: 'center', padding: '4rem' }}>
          <Users size={48} color="var(--text-muted)" style={{ marginBottom: '1rem' }}/>
          <h3 style={{ fontFamily: 'Outfit', marginBottom: '1rem' }}>No Applications Yet</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Run a user assessment to start seeing data here.</p>
          <button className="btn-primary" onClick={() => navigate('/assess')} style={{ width: 'auto' }}>Run First Assessment</button>
        </div>
      ) : (
        <>
          {/* ── KPI ROW ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
            <div className="glass-card-cred" style={kpiStyle}>
              <div style={kpiValue(totalApps)}>{totalApps}</div>
              <div style={kpiLabel}>Applications</div>
            </div>
            <div className="glass-card-cred" style={kpiStyle}>
              <div style={kpiValue(avgScore)}>{avgScore}</div>
              <div style={kpiLabel}>Avg Score</div>
            </div>
            <div className="glass-card-cred" style={kpiStyle}>
              <div style={kpiValue(approvalRate + '%')}>{approvalRate}%</div>
              <div style={kpiLabel}>Approval Rate</div>
            </div>
            <div className="glass-card-cred" style={kpiStyle}>
              <div style={kpiValue((avgILF * 100).toFixed(0) + '%')}>{(avgILF * 100).toFixed(0)}%</div>
              <div style={kpiLabel}>Avg ILF Score</div>
            </div>
            <div className="glass-card-cred" style={kpiStyle}>
              <div style={kpiValue(flaggedCount, flaggedCount > 0 ? 'var(--danger)' : 'var(--neon-mint)')}>{flaggedCount}</div>
              <div style={kpiLabel}>Flagged Sessions</div>
            </div>
          </div>

          {/* ── LLM SESSIONS CARD ── */}
          {llmStats && llmStats.total_sessions > 0 && (
            <div className="glass-card-cred" style={{ marginBottom: '3rem', padding: '2rem' }}>
              <h3 style={{ fontFamily: 'Outfit', marginBottom: '1.5rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <BrainCircuit size={20} color="var(--neon-mint)"/> Adaptive AI Interviews
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Outfit', fontSize: '2rem', fontWeight: 800, color: 'var(--neon-mint)' }}>{llmStats.completed_sessions}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Completed</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Outfit', fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>{llmStats.avg_questions_per_session}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Avg Questions</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Outfit', fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>{llmStats.llm_sessions}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Gemini Sessions</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Outfit', fontSize: '2rem', fontWeight: 800, color: '#F59E0B' }}>{llmStats.mock_sessions}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Mock Sessions</div>
                </div>
              </div>

              {/* LLM Session Table */}
              {llmSessions.length > 0 && (
                <div style={{ marginTop: '1.5rem', overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        {['Applicant', 'Score', 'Decision', 'Questions', 'Confidence', 'Mode', ''].map(h => (
                          <th key={h} style={{ padding: '0.8rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase', fontSize: '0.7rem' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {llmSessions.slice(0, 10).map((s, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '0.8rem', fontWeight: 600 }}>{s.name}</td>
                          <td style={{ padding: '0.8rem', fontFamily: 'Outfit', fontWeight: 700, color: (s.final_score||0) >= 700 ? 'var(--neon-mint)' : (s.final_score||0) >= 450 ? '#F59E0B' : 'var(--danger)' }}>{s.final_score || '—'}</td>
                          <td style={{ padding: '0.8rem' }}><span style={{ background: (DECISION_COLORS[s.decision]||'#888') + '22', color: DECISION_COLORS[s.decision]||'#888', padding: '0.2rem 0.6rem', borderRadius: '50px', fontSize: '0.75rem', fontWeight: 600 }}>{s.decision || '—'}</span></td>
                          <td style={{ padding: '0.8rem' }}>{s.total_turns || 0}</td>
                          <td style={{ padding: '0.8rem', textTransform: 'capitalize' }}>{s.extraction_confidence || '—'}</td>
                          <td style={{ padding: '0.8rem' }}><span style={{ fontSize: '0.75rem', color: s.is_mock_mode ? '#F59E0B' : 'var(--neon-mint)' }}>{s.is_mock_mode ? 'Mock' : 'Gemini'}</span></td>
                          <td style={{ padding: '0.8rem' }}><button onClick={() => openSessionDetail(s.session_id)} style={{ background: 'none', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)', borderRadius: '6px', padding: '0.3rem 0.8rem', cursor: 'pointer', fontSize: '0.75rem' }}>View</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── CHARTS ROW ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '1.5rem', marginBottom: '3rem' }}>
            {/* Score Distribution */}
            <div className="glass-card-cred">
              <h3 style={{ fontFamily: 'Outfit', marginBottom: '1.5rem', fontSize: '1.2rem' }}>Score Distribution</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={scoreHistData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                  <XAxis dataKey="range" tick={{ fill: '#8E8E93', fontSize: 11 }}/>
                  <YAxis tick={{ fill: '#8E8E93', fontSize: 11 }}/>
                  <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '8px', color: 'white' }}/>
                  <Bar dataKey="count" fill="#00FF9D" radius={[4,4,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Risk Tier Pie */}
            <div className="glass-card-cred" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <h3 style={{ fontFamily: 'Outfit', marginBottom: '1rem', fontSize: '1.2rem' }}>Risk Tiers</h3>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={riskData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={5}>
                    {riskData.map(entry => <Cell key={entry.name} fill={RISK_COLORS[entry.name]}/>)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '8px', color: 'white' }}/>
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
                {riskData.map(r => <span key={r.name} style={{ color: RISK_COLORS[r.name] }}>{r.name}: {r.value}</span>)}
              </div>
            </div>

            {/* Decision Pie */}
            <div className="glass-card-cred" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <h3 style={{ fontFamily: 'Outfit', marginBottom: '1rem', fontSize: '1.2rem' }}>Decisions</h3>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={decisionData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={5}>
                    {decisionData.map(entry => <Cell key={entry.name} fill={DECISION_COLORS[entry.name]}/>)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '8px', color: 'white' }}/>
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
                {decisionData.map(d => <span key={d.name} style={{ color: DECISION_COLORS[d.name] }}>{d.name}: {d.value}</span>)}
              </div>
            </div>
          </div>

          {/* ── MODEL HEALTH + CPS ALERTS ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '3rem' }}>
            <div className="glass-card-cred">
              <h3 style={{ fontFamily: 'Outfit', marginBottom: '1.5rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldCheck size={20} color="var(--neon-mint)"/> Model Health
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.2)', borderRadius: '12px', padding: '1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>Causal Logistic Regression</strong>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>AUC Normal: 0.858 | Recession: 0.856</div>
                  </div>
                  <span style={{ color: 'var(--neon-mint)', fontWeight: 700 }}>STABLE</span>
                </div>
                <div style={{ background: 'rgba(255,59,48,0.08)', border: '1px solid rgba(255,59,48,0.2)', borderRadius: '12px', padding: '1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>XGBoost (Black-Box)</strong>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>AUC Normal: 0.944 | Recession: 0.411</div>
                  </div>
                  <span style={{ color: 'var(--danger)', fontWeight: 700 }}>QUARANTINED</span>
                </div>
              </div>
            </div>

            <div className="glass-card-cred">
              <h3 style={{ fontFamily: 'Outfit', marginBottom: '1.5rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <AlertTriangle size={20} color="var(--danger)"/> CPS Drift Alerts
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: 'rgba(255,59,48,0.08)', border: '1px solid rgba(255,59,48,0.2)', borderRadius: '12px', padding: '1rem' }}>
                  <strong style={{ color: 'var(--danger)' }}>dark_mode_user</strong>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>CPS 0.72 &rarr; 0.35. Spurious reversal detected.</div>
                </div>
                <div style={{ background: 'rgba(255,59,48,0.08)', border: '1px solid rgba(255,59,48,0.2)', borderRadius: '12px', padding: '1rem' }}>
                  <strong style={{ color: 'var(--danger)' }}>social_media_score</strong>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>CPS 0.65 &rarr; 0.28. Drifting under recession.</div>
                </div>
                <div style={{ background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.2)', borderRadius: '12px', padding: '1rem' }}>
                  <strong style={{ color: 'var(--neon-mint)' }}>income_mean, utility_rate, dti_final</strong>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>All causal features stable. CPS &gt; 0.85.</div>
                </div>
              </div>
            </div>
          </div>

          {/* ── KNOWLEDGE GRAPH INSIGHTS ── */}
          {kgStats && kgStats.total_nodes > 0 && (
            <div className="glass-card-cred" style={{ marginBottom: '3rem', padding: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ fontFamily: 'Outfit', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Network size={20} color="#A855F7"/> Knowledge Graph Intelligence
                </h3>
                <button onClick={() => navigate('/knowledge-graph')} style={{ background: 'none', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)', borderRadius: '8px', padding: '0.4rem 1rem', cursor: 'pointer', fontSize: '0.75rem', fontFamily: 'Inter' }}>Explore Full Graph →</button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                {[
                  ['Nodes', kgStats.total_nodes, '#A855F7'],
                  ['Edges', kgStats.total_edges, '#A855F7'],
                  ['Borrowers', kgStats.borrower_count || 0, '#00FF9D'],
                  ['Avg Degree', kgStats.avg_degree || 0, '#3B82F6'],
                  ['Components', kgStats.connected_components || 0, '#F59E0B'],
                ].map(([label, val, color]) => (
                  <div key={label} style={{ textAlign: 'center' }}>
                    <div style={{ fontFamily: 'Outfit', fontSize: '1.6rem', fontWeight: 800, color }}>{val}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', letterSpacing: '1px', textTransform: 'uppercase' }}>{label}</div>
                  </div>
                ))}
              </div>
              {kgInsights && kgInsights.insights && kgInsights.insights.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.8rem' }}>
                  {kgInsights.insights.slice(0, 4).map((ins, i) => (
                    <div key={i} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '1rem' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>{ins.title}</div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{ins.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── APPLICATION LOG TABLE ── */}
          <div className="glass-card-cred">
            <h3 style={{ fontFamily: 'Outfit', marginBottom: '1.5rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Users size={20}/> Application Log
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    {['Applicant', 'Score', 'Decision', 'Risk', 'ILF', 'Flagged', 'Time'].map(h => (
                      <th key={h} style={{ padding: '1rem 0.8rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase', fontSize: '0.75rem' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...apps].reverse().map((a, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '1rem 0.8rem', fontWeight: 600 }}>{a.demo_user || 'Unknown'}</td>
                      <td style={{ padding: '1rem 0.8rem', fontFamily: 'Outfit', fontWeight: 700, color: a.score >= 700 ? 'var(--neon-mint)' : a.score >= 450 ? 'var(--warning)' : 'var(--danger)' }}>{a.score}</td>
                      <td style={{ padding: '1rem 0.8rem' }}>
                        <span style={{ background: DECISION_COLORS[a.decision] + '22', color: DECISION_COLORS[a.decision], padding: '0.3rem 0.8rem', borderRadius: '50px', fontSize: '0.8rem', fontWeight: 600 }}>{a.decision}</span>
                      </td>
                      <td style={{ padding: '1rem 0.8rem', color: RISK_COLORS[a.risk_tier] }}>{a.risk_tier}</td>
                      <td style={{ padding: '1rem 0.8rem' }}>{a.ilf_reliability ? (a.ilf_reliability * 100).toFixed(0) + '%' : 'N/A'}</td>
                      <td style={{ padding: '1rem 0.8rem' }}>{a.catch_trial_flagged ? <AlertTriangle size={16} color="var(--danger)"/> : <CheckCircle2 size={16} color="var(--neon-mint)"/>}</td>
                      <td style={{ padding: '1rem 0.8rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>{a.timestamp ? new Date(a.timestamp).toLocaleString() : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ── SESSION DRILL-DOWN MODAL ── */}
      {selectedSession && sessionDetail && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem' }} onClick={() => { setSelectedSession(null); setSessionDetail(null); }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '20px', padding: '2.5rem', maxWidth: '700px', width: '100%', maxHeight: '80vh', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', marginBottom: '0.5rem' }}>
              {sessionDetail.session?.name || 'Session Detail'}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '2rem' }}>
              Score: <strong style={{ color: 'var(--neon-mint)' }}>{sessionDetail.session?.final_score || '—'}</strong> | Decision: <strong>{sessionDetail.session?.decision || '—'}</strong> | Confidence: {sessionDetail.session?.extraction_confidence || '—'}
            </p>

            {/* Extracted Features */}
            {sessionDetail.session?.extracted_features && (
              <div style={{ marginBottom: '2rem', background: 'rgba(0,255,157,0.05)', border: '1px solid rgba(0,255,157,0.15)', borderRadius: '12px', padding: '1.2rem' }}>
                <h4 style={{ fontFamily: 'Outfit', fontSize: '0.9rem', color: 'var(--neon-mint)', marginBottom: '1rem', letterSpacing: '1px', textTransform: 'uppercase' }}>Extracted Features</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.8rem' }}>
                  {Object.entries(sessionDetail.session.extracted_features).map(([k, v]) => (
                    <div key={k} style={{ fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{k}:</span> <strong>{typeof v === 'number' ? v.toFixed(3) : v}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Conversation Transcript */}
            <h4 style={{ fontFamily: 'Outfit', fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem', letterSpacing: '1px', textTransform: 'uppercase' }}>Conversation Transcript</h4>
            {(sessionDetail.session?.qa_history || []).map((qa, i) => (
              <div key={i} style={{ marginBottom: '1.2rem', paddingLeft: '1rem', borderLeft: '2px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '4px', fontWeight: 500 }}>Q{i+1}: {qa.q}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--neon-mint)' }}>→ {qa.a}</div>
              </div>
            ))}

            <button className="btn-outline" onClick={() => { setSelectedSession(null); setSessionDetail(null); }} style={{ marginTop: '1rem', width: '100%' }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
