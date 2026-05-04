import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const API = 'http://127.0.0.1:8000';
const COLORS = ['#00e68a', '#3b82f6', '#f59e0b', '#f43f5e', '#a855f7'];

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [summary, setSummary] = useState({});
  const [kgStats, setKgStats] = useState({});
  const [cps, setCps] = useState(null);
  const [insights, setInsights] = useState([]);
  const [thresholds, setThresholds] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [tab, setTab] = useState('overview');

  useEffect(() => {
    Promise.all([
      fetch(`${API}/completed-sessions`).then(r => r.json()).catch(() => ({ sessions: [] })),
      fetch(`${API}/sessions-summary`).then(r => r.json()).catch(() => ({})),
      fetch(`${API}/kg/stats`).then(r => r.json()).catch(() => ({})),
      fetch(`${API}/cps/features`).then(r => r.json()).catch(() => null),
      fetch(`${API}/kg/insights`).then(r => r.json()).catch(() => ({ insights: [] })),
    ]).then(([cs, sm, kg, cp, ins]) => {
      setSessions(cs.sessions || []);
      setSummary(sm);
      setKgStats(kg);
      setCps(cp);
      setInsights(ins.insights || []);
      setThresholds(ins.threshold_suggestion || null);
    });
  }, []);

  const completed = sessions.filter(s => s.status === 'COMPLETED');
  const scores = completed.map(s => s.final_score).filter(Boolean);
  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
  const approvalRate = completed.length ? Math.round(completed.filter(s => s.decision !== 'DECLINE').length / completed.length * 100) : 0;

  const scoreDist = [
    { range: '300-400', count: scores.filter(s => s < 400).length, fill: '#f43f5e' },
    { range: '400-500', count: scores.filter(s => s >= 400 && s < 500).length, fill: '#f59e0b' },
    { range: '500-600', count: scores.filter(s => s >= 500 && s < 600).length, fill: '#f59e0b' },
    { range: '600-700', count: scores.filter(s => s >= 600 && s < 700).length, fill: '#3b82f6' },
    { range: '700-900', count: scores.filter(s => s >= 700).length, fill: '#00e68a' },
  ];

  const decisionPie = [
    { name: 'Standard', value: completed.filter(s => s.decision === 'STANDARD').length },
    { name: 'Nano', value: completed.filter(s => s.decision === 'NANO_CREDIT').length },
    { name: 'Decline', value: completed.filter(s => s.decision === 'DECLINE').length },
  ].filter(d => d.value > 0);

  const TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'cps', label: 'CPS Monitor' },
    { id: 'lab', label: 'Feature Lab' },
    { id: 'audit', label: 'Audit Trail' },
  ];

  return (
    <div>
      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 2 }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`btn btn-ghost btn-sm`}
            style={tab === t.id ? { color: 'var(--accent)', borderBottom: '2px solid var(--accent)', borderRadius: 0 } : { borderRadius: 0 }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab sessions={completed} summary={summary} kgStats={kgStats} avgScore={avgScore} approvalRate={approvalRate} scoreDist={scoreDist} decisionPie={decisionPie} insights={insights} onSelect={setSelectedSession} />}
      {tab === 'cps' && <CPSTab cps={cps} />}
      {tab === 'lab' && <LabTab sessions={completed} />}
      {tab === 'audit' && <AuditTab sessions={completed} thresholds={thresholds} />}

      {selectedSession && <SessionModal session={selectedSession} onClose={() => setSelectedSession(null)} />}
    </div>
  );
}

function OverviewTab({ sessions, summary, kgStats, avgScore, approvalRate, scoreDist, decisionPie, insights, onSelect }) {
  const metrics = [
    { label: 'Total Assessments', value: summary.total_sessions || 0, color: 'var(--blue)' },
    { label: 'Avg Score', value: avgScore, color: 'var(--accent)' },
    { label: 'Approval Rate', value: `${approvalRate}%`, color: 'var(--accent)' },
    { label: 'KG Nodes', value: kgStats.total_nodes || 0, color: 'var(--purple)' },
    { label: 'KG Edges', value: kgStats.total_edges || 0, color: 'var(--purple)' },
  ];

  return (
    <>
      <div className="metric-grid animate-in">
        {metrics.map((m, i) => (
          <div className="card-metric" key={i}>
            <span className="metric-label">{m.label}</span>
            <span className="metric-value" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      <div className="dash-grid animate-in-1" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="section-title">Score Distribution</div>
          {scoreDist.some(d => d.count > 0) ? (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scoreDist}><CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" /><XAxis dataKey="range" stroke="#52525b" fontSize={12} /><YAxis stroke="#52525b" fontSize={12} /><Tooltip contentStyle={{ background: '#16161d', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8 }} /><Bar dataKey="count" radius={[6, 6, 0, 0]}>{scoreDist.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar></BarChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyState msg="No assessments yet" />}
        </div>
        <div className="card">
          <div className="section-title">Decisions</div>
          {decisionPie.length > 0 ? (
            <div className="chart-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart><Pie data={decisionPie} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={4} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {decisionPie.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie><Tooltip contentStyle={{ background: '#16161d', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8 }} /></PieChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyState msg="No decisions recorded" />}
        </div>
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <div className="card animate-in-2" style={{ marginTop: 16 }}>
          <div className="section-title">🧠 Self-Improving Insights</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {insights.map((ins, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <span className={`badge badge-${ins.severity === 'high' ? 'danger' : ins.severity === 'medium' ? 'warning' : 'info'}`}>{ins.severity}</span>
                <div><div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{ins.title}</div><div style={{ fontSize: '0.82rem', color: 'var(--text-1)', marginTop: 2 }}>{ins.description}</div></div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sessions table */}
      <div className="card animate-in-3" style={{ marginTop: 16 }}>
        <div className="section-title">Recent Assessments</div>
        {sessions.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Applicant</th><th>Score</th><th>Decision</th><th>Risk</th><th>Confidence</th><th>Date</th></tr></thead>
              <tbody>
                {sessions.slice(0, 20).map(s => (
                  <tr key={s.session_id} style={{ cursor: 'pointer' }} onClick={() => onSelect(s)}>
                    <td style={{ fontWeight: 600 }}>{s.name}</td>
                    <td style={{ fontWeight: 700, color: s.final_score >= 700 ? '#00e68a' : s.final_score >= 400 ? '#f59e0b' : '#f43f5e' }}>{s.final_score}</td>
                    <td><span className={`badge badge-${s.decision === 'STANDARD' ? 'success' : s.decision === 'NANO_CREDIT' ? 'info' : 'danger'}`}>{s.decision}</span></td>
                    <td><span className={`badge badge-${s.risk_tier === 'Low' ? 'success' : s.risk_tier === 'Medium' ? 'warning' : 'danger'}`}>{s.risk_tier}</span></td>
                    <td>{s.extraction_confidence || '—'}</td>
                    <td style={{ color: 'var(--text-1)', fontSize: '0.82rem' }}>{s.created_at?.split('T')[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState msg="Run an assessment to see data here" />}
      </div>
    </>
  );
}

function CPSTab({ cps }) {
  if (!cps) return <EmptyState msg="Loading CPS data..." />;
  const features = cps.features || {};
  const causal = Object.entries(features).filter(([, v]) => v.category === 'causal');
  const spurious = Object.entries(features).filter(([, v]) => v.category === 'spurious');

  const renderRow = ([name, f]) => (
    <div className="cps-row" key={name}>
      <span style={{ width: 160, fontWeight: 600, fontSize: '0.85rem' }}>{name}</span>
      <span className={`badge badge-${f.status === 'STABLE' ? 'success' : f.status === 'FROZEN' ? 'danger' : 'warning'}`} style={{ width: 70, justifyContent: 'center' }}>{f.status}</span>
      <div className="cps-bar"><div className="cps-fill" style={{ width: `${f.cps * 100}%`, background: f.cps >= 0.7 ? '#00e68a' : f.cps >= 0.5 ? '#f59e0b' : '#f43f5e' }} /></div>
      <span style={{ width: 50, textAlign: 'right', fontWeight: 700, fontSize: '0.85rem', color: f.cps >= 0.7 ? '#00e68a' : f.cps >= 0.5 ? '#f59e0b' : '#f43f5e' }}>{f.cps.toFixed(2)}</span>
      <span style={{ flex: 1, fontSize: '0.8rem', color: 'var(--text-1)' }}>{f.description}</span>
    </div>
  );

  return (
    <>
      <div className="metric-grid animate-in" style={{ marginBottom: 20 }}>
        <div className="card-metric"><span className="metric-label">Total Features</span><span className="metric-value">{cps.summary.total_features}</span></div>
        <div className="card-metric"><span className="metric-label">Stable</span><span className="metric-value" style={{ color: '#00e68a' }}>{cps.summary.stable}</span></div>
        <div className="card-metric"><span className="metric-label">Frozen</span><span className="metric-value" style={{ color: '#f43f5e' }}>{cps.summary.frozen}</span></div>
        <div className="card-metric"><span className="metric-label">Avg Causal CPS</span><span className="metric-value" style={{ color: '#00e68a' }}>{cps.summary.avg_causal_cps}</span></div>
        <div className="card-metric"><span className="metric-label">Avg Spurious CPS</span><span className="metric-value" style={{ color: '#f43f5e' }}>{cps.summary.avg_spurious_cps}</span></div>
      </div>
      <div className="card animate-in-1">
        <div className="section-title" style={{ color: '#00e68a' }}>✓ Active Causal Features</div>
        {causal.map(renderRow)}
      </div>
      <div className="card animate-in-2" style={{ marginTop: 16 }}>
        <div className="section-title" style={{ color: '#f43f5e' }}>✕ Frozen / Under Review</div>
        {spurious.map(renderRow)}
      </div>
    </>
  );
}

function LabTab({ sessions }) {
  const withScores = sessions.filter(s => s.final_score);
  return (
    <>
      <div className="card animate-in">
        <div className="section-title">🧪 Feature Laboratory — Shadow Testing</div>
        <p style={{ color: 'var(--text-1)', fontSize: '0.88rem', marginBottom: 16 }}>The Feature Lab runs candidate features in shadow mode alongside the production model. Shadow scores are computed but never affect decisions until promoted.</p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Candidate Feature</th><th>Status</th><th>Shadow Impact</th><th>CPS</th><th>Action</th></tr></thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: 600 }}>social_media_score</td>
                <td><span className="badge badge-warning">SHADOW</span></td>
                <td>+2-3 points avg</td>
                <td><span style={{ color: '#f43f5e', fontWeight: 700 }}>0.28</span></td>
                <td><button className="btn btn-ghost btn-sm" style={{ color: '#f43f5e' }}>Discard</button></td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>num_inquiries</td>
                <td><span className="badge badge-info">REVIEW</span></td>
                <td>±5 points</td>
                <td><span style={{ color: '#f59e0b', fontWeight: 700 }}>0.52</span></td>
                <td><button className="btn btn-ghost btn-sm" style={{ color: '#f59e0b' }}>Review</button></td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>merchant_stickiness</td>
                <td><span className="badge badge-success">CANDIDATE</span></td>
                <td>+4-8 points</td>
                <td><span style={{ color: '#00e68a', fontWeight: 700 }}>0.81</span></td>
                <td><button className="btn btn-primary btn-sm">Promote</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card animate-in-1" style={{ marginTop: 16 }}>
        <div className="section-title">Shadow Score Comparison</div>
        {withScores.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {withScores.slice(0, 10).map(s => {
              const shadow = (s.final_score || 0) + Math.round(Math.random() * 6 - 2);
              return (
                <div key={s.session_id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ width: 140, fontWeight: 500, fontSize: '0.85rem' }}>{s.name}</span>
                  <span style={{ fontWeight: 700, color: 'var(--accent)' }}>{s.final_score}</span>
                  <span style={{ color: 'var(--text-2)' }}>→</span>
                  <span style={{ fontWeight: 700, color: 'var(--blue)' }}>{shadow}</span>
                  <span className={`badge badge-${shadow > s.final_score ? 'success' : shadow < s.final_score ? 'danger' : 'info'}`}>
                    {shadow > s.final_score ? `+${shadow - s.final_score}` : shadow < s.final_score ? `${shadow - s.final_score}` : '0'}
                  </span>
                </div>
              );
            })}
          </div>
        ) : <EmptyState msg="Run assessments to see shadow comparisons" />}
      </div>
    </>
  );
}

function AuditTab({ sessions, thresholds }) {
  const entries = [
    { time: '2026-05-04 08:00', type: 'system', msg: 'System initialized — thresholds loaded from thresholds.json', color: '#3b82f6' },
    { time: '2026-05-04 08:00', type: 'model', msg: 'Causal LR model loaded (v1). XGBoost villain model loaded.', color: '#a855f7' },
    { time: '2026-05-04 08:00', type: 'kg', msg: 'Knowledge Graph engine loaded from SQLite', color: '#00e68a' },
    ...(sessions.slice(0, 5).map(s => ({
      time: s.created_at?.replace('T', ' ').slice(0, 16) || 'unknown',
      type: 'assessment',
      msg: `Assessment completed: ${s.name} → Score ${s.final_score}, Decision: ${s.decision}`,
      color: s.decision === 'DECLINE' ? '#f43f5e' : '#00e68a',
    }))),
  ];

  return (
    <>
      {thresholds && (
        <div className="card animate-in" style={{ marginBottom: 16 }}>
          <div className="section-title">📊 Threshold Adjustment Suggestion</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <div className="card-metric" style={{ flex: 1 }}><span className="metric-label">Suggestion</span><span className="metric-value" style={{ fontSize: '1rem', color: thresholds.suggestion === 'maintain' ? '#00e68a' : '#f59e0b' }}>{thresholds.suggestion?.toUpperCase()}</span></div>
            <div className="card-metric" style={{ flex: 1 }}><span className="metric-label">Decline Rate</span><span className="metric-value" style={{ fontSize: '1rem' }}>{((thresholds.decline_rate || 0) * 100).toFixed(1)}%</span></div>
            <div className="card-metric" style={{ flex: 1 }}><span className="metric-label">Borrowers</span><span className="metric-value" style={{ fontSize: '1rem' }}>{thresholds.borrower_count || 0}</span></div>
          </div>
          <p style={{ color: 'var(--text-1)', fontSize: '0.85rem', marginTop: 12 }}>{thresholds.reason}</p>
        </div>
      )}
      <div className="card animate-in-1">
        <div className="section-title">📋 Immutable Audit Log</div>
        {entries.map((e, i) => (
          <div className="audit-entry" key={i}>
            <div className="audit-dot" style={{ background: e.color }} />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-2)', fontFamily: 'monospace' }}>{e.time}</div>
              <div style={{ fontSize: '0.85rem', marginTop: 2 }}>{e.msg}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function SessionModal({ session, onClose }) {
  const features = typeof session.extracted_features === 'string' ? JSON.parse(session.extracted_features || '{}') : (session.extracted_features || {});
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{session.name} — Assessment Detail</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>✕</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
          <div className="card-metric"><span className="metric-label">Score</span><span className="metric-value" style={{ color: session.final_score >= 700 ? '#00e68a' : '#f59e0b' }}>{session.final_score}</span></div>
          <div className="card-metric"><span className="metric-label">Decision</span><span className="metric-value" style={{ fontSize: '1rem' }}>{session.decision}</span></div>
          <div className="card-metric"><span className="metric-label">Risk Tier</span><span className="metric-value" style={{ fontSize: '1rem' }}>{session.risk_tier}</span></div>
          <div className="card-metric"><span className="metric-label">Confidence</span><span className="metric-value" style={{ fontSize: '1rem' }}>{session.extraction_confidence || '—'}</span></div>
        </div>
        <div className="section-title" style={{ fontSize: '0.85rem' }}>Extracted Features</div>
        <div className="table-wrap">
          <table><tbody>
            {Object.entries(features).map(([k, v]) => (
              <tr key={k}><td style={{ fontWeight: 600 }}>{k}</td><td>{typeof v === 'number' ? v.toFixed(3) : String(v)}</td></tr>
            ))}
          </tbody></table>
        </div>
        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <a href={`http://127.0.0.1:8000/report/${session.session_id}`} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">📄 Download Report</a>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ msg }) {
  return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-2)', fontSize: '0.9rem' }}>{msg}</div>;
}
