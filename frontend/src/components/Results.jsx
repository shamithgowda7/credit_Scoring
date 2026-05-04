import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export default function Results() {
  const { state } = useLocation();
  const nav = useNavigate();
  const [showForensics, setShowForensics] = useState(false);
  const [animScore, setAnimScore] = useState(300);
  const scoreResult = state?.scoreResult;

  useEffect(() => {
    if (!scoreResult) { nav('/assess'); return; }
    const target = scoreResult.score || 0;
    const dur = 1200;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setAnimScore(Math.round(300 + (target - 300) * eased));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [scoreResult]);

  if (!scoreResult) return null;

  const { score, decision, risk_tier, contributions, product, ignored_features, improvement_notes, rud_boost, graph_features, graph_boost, ilf_boost, ilf_reliability, shadow_score } = scoreResult;
  const scoreColor = score >= 700 ? '#00e68a' : score >= 400 ? '#f59e0b' : '#f43f5e';
  const decisionClass = decision === 'STANDARD' ? 'approved' : decision === 'DECLINE' ? 'declined' : 'nano';
  const pct = ((score - 300) / 600) * 100;
  const circ = 2 * Math.PI * 80;

  const contribEntries = Object.entries(contributions || {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const maxContrib = Math.max(...contribEntries.map(([, v]) => Math.abs(v)), 0.01);

  return (
    <div className="results-page">
      <div className="results-hero animate-in">
        <div className="score-ring">
          <svg width="200" height="200" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="80" fill="none" stroke="var(--bg-3)" strokeWidth="8" />
            <circle cx="100" cy="100" r="80" fill="none" stroke={scoreColor} strokeWidth="8"
              strokeDasharray={circ} strokeDashoffset={circ - (circ * pct / 100)} strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 1.2s ease' }} />
          </svg>
          <span className="score-value" style={{ color: scoreColor }}>{animScore}</span>
          <span className="score-label">Credit Score</span>
        </div>

        <div className={`decision-card ${decisionClass}`} style={{ marginTop: 20 }}>
          <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>
            {decision === 'STANDARD' ? '✓ Approved' : decision === 'DECLINE' ? '✕ Declined' : '◐ Nano Credit'}
          </span>
          {product && <span>— ₹{product.amount?.toLocaleString()} {product.insurance ? '+ Insurance' : ''}</span>}
        </div>
      </div>

      {/* Boosts summary */}
      <div className="metric-grid animate-in-1" style={{ marginTop: 20 }}>
        <div className="card-metric">
          <span className="metric-label">Risk Tier</span>
          <span className="metric-value" style={{ fontSize: '1.2rem', color: risk_tier === 'Low' ? '#00e68a' : risk_tier === 'Medium' ? '#f59e0b' : '#f43f5e' }}>{risk_tier}</span>
        </div>
        {rud_boost > 0 && <div className="card-metric"><span className="metric-label">RUD Boost</span><span className="metric-value" style={{ fontSize: '1.2rem', color: '#00e68a' }}>+{rud_boost}</span></div>}
        {graph_boost !== 0 && <div className="card-metric"><span className="metric-label">Graph Boost</span><span className="metric-value" style={{ fontSize: '1.2rem', color: graph_boost > 0 ? '#00e68a' : '#f43f5e' }}>{graph_boost > 0 ? '+' : ''}{graph_boost}</span></div>}
        {ilf_boost !== 0 && <div className="card-metric"><span className="metric-label">ILF Boost</span><span className="metric-value" style={{ fontSize: '1.2rem', color: ilf_boost > 0 ? '#00e68a' : '#f43f5e' }}>{ilf_boost > 0 ? '+' : ''}{ilf_boost}</span></div>}
        {shadow_score && <div className="card-metric"><span className="metric-label">Shadow Score</span><span className="metric-value" style={{ fontSize: '1.2rem', color: 'var(--blue)' }}>{shadow_score}</span></div>}
      </div>

      {/* Improvement notes */}
      {improvement_notes && (
        <div className="card animate-in-2" style={{ marginTop: 16, borderColor: 'var(--border-accent)' }}>
          <div className="section-title" style={{ color: 'var(--accent)' }}>📈 Self-Improving Feedback</div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-1)', lineHeight: 1.6 }}>{improvement_notes}</p>
        </div>
      )}

      {/* Forensic Mode */}
      <div className="forensics-section animate-in-3">
        <div className="forensics-toggle" style={{ marginTop: 16 }}>
          <div className={`toggle-switch${showForensics ? ' on' : ''}`} onClick={() => setShowForensics(!showForensics)} />
          <span style={{ fontWeight: 600 }}>Forensic Explainability — Why this score?</span>
        </div>

        {showForensics && (
          <div style={{ animation: 'fade-in 0.3s ease' }}>
            {/* Causal drivers */}
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ color: '#00e68a', fontSize: '0.88rem' }}>✓ Verified Causal Drivers</div>
              {contribEntries.map(([feat, val]) => (
                <div className="contrib-bar" key={feat}>
                  <span className="bar-label">{feat}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${Math.abs(val) / maxContrib * 100}%`, background: val > 0 ? '#f43f5e' : '#00e68a' }} />
                  </div>
                  <span className="bar-value" style={{ color: val > 0 ? '#f43f5e' : '#00e68a' }}>{val > 0 ? '+' : ''}{val.toFixed(3)}</span>
                </div>
              ))}
              <p style={{ fontSize: '0.78rem', color: 'var(--text-2)', marginTop: 8 }}>Positive = increases default risk. Negative = decreases default risk.</p>
            </div>

            {/* Ignored spurious features */}
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ color: '#f43f5e', fontSize: '0.88rem' }}>✕ Ignored Spurious Features</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(ignored_features || []).map((f, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '6px 10px', background: 'var(--rose-dim)', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem' }}>
                    <span style={{ color: '#f43f5e', fontWeight: 700 }}>BLOCKED</span>
                    <span style={{ fontWeight: 600 }}>{f.name}</span>
                    <span style={{ color: 'var(--text-1)' }}>— {f.description}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* ILF Biometrics */}
            {ilf_reliability !== null && ilf_reliability !== undefined && (
              <div className="card">
                <div className="section-title" style={{ fontSize: '0.88rem' }}>🧠 Behavioral Biometrics (ILF)</div>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  <div className="card-metric"><span className="metric-label">ILF Reliability</span><span className="metric-value" style={{ fontSize: '1.1rem' }}>{(ilf_reliability * 100).toFixed(0)}%</span></div>
                  <div className="card-metric"><span className="metric-label">Score Impact</span><span className="metric-value" style={{ fontSize: '1.1rem', color: ilf_boost >= 0 ? '#00e68a' : '#f43f5e' }}>{ilf_boost >= 0 ? '+' : ''}{ilf_boost} pts</span></div>
                </div>
              </div>
            )}

            {/* Graph features */}
            {graph_features && (
              <div className="card" style={{ marginTop: 12 }}>
                <div className="section-title" style={{ fontSize: '0.88rem' }}>🕸️ Knowledge Graph Context</div>
                <div className="table-wrap">
                  <table><tbody>
                    {Object.entries(graph_features).filter(([k]) => k !== 'graph_risk_adjustment').map(([k, v]) => (
                      <tr key={k}><td style={{ fontWeight: 600 }}>{k}</td><td>{typeof v === 'number' ? v.toFixed(3) : String(v)}</td></tr>
                    ))}
                  </tbody></table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }} className="animate-in-4">
        <button className="btn btn-primary" onClick={() => nav('/assess')}>Run Another Assessment</button>
        <button className="btn btn-secondary" onClick={() => nav('/dashboard')}>View Dashboard</button>
        {state?.sessionId && (
          <a href={`http://127.0.0.1:8000/report/${state.sessionId}`} target="_blank" rel="noreferrer" className="btn btn-secondary">📄 Adverse Action Report</a>
        )}
      </div>
    </div>
  );
}
