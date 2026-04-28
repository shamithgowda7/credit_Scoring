import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ShieldAlert, ActivitySquare, BrainCircuit } from 'lucide-react';

export default function Results() {
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [ilf, setIlf] = useState(null);
  const [user, setUser] = useState(null);
  
  const [recessionMode, setRecessionMode] = useState(false);
  const [showForensics, setShowForensics] = useState(false);

  useEffect(() => {
    const resStr = sessionStorage.getItem('scoreResult');
    const ilfStr = sessionStorage.getItem('ilfResult');
    const usrStr = sessionStorage.getItem('selectedUser');
    
    if (!resStr) {
      navigate('/assess');
      return;
    }
    setResult(JSON.parse(resStr));
    if (ilfStr) setIlf(JSON.parse(ilfStr));
    if (usrStr) setUser(JSON.parse(usrStr));
  }, [navigate]);

  if (!result) return null;

  const { score, decision, product, xgboost_score, ignored_features, contributions } = result;
  const isCrashed = recessionMode && xgboost_score < score - 50;

  return (
    <div className="slide-up" style={{ paddingBottom: '4rem' }}>
      
      {/* ── TACTILE RECESSION TOGGLE ── */}
      <div className="glass-card-cred" style={{ marginBottom: '3rem', padding: '1.5rem 2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderColor: recessionMode ? 'var(--danger)' : 'var(--border-subtle)' }}>
        <div>
          <h3 style={{ fontFamily: 'Outfit', fontSize: '1.2rem', color: recessionMode ? 'var(--danger)' : 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
            <ActivitySquare size={20} />
            Recession Stress Test
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '0.5rem 0 0' }}>
            Toggle to simulate a macroeconomic shock on standard vs causal AI.
          </p>
        </div>
        <label className="tactile-switch">
          <input type="checkbox" checked={recessionMode} onChange={() => setRecessionMode(!recessionMode)} />
          <span className="tactile-slider"></span>
        </label>
      </div>

      {/* ── SCORE REVEAL ── */}
      <div style={{ display: 'flex', gap: '2rem', marginBottom: '3rem', flexWrap: 'wrap' }}>
        
        {/* Causal AI Card */}
        <div className="glass-card-cred" style={{ flex: 1, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '4px', background: 'var(--neon-mint)' }}></div>
          <p style={{ color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', fontSize: '0.8rem', fontWeight: 600 }}>Causal Engine</p>
          <div className="score-big" style={{ margin: '2rem 0' }}>{score}</div>
          <p style={{ color: 'var(--neon-mint)', fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} /> Stable Baseline
          </p>
        </div>

        {/* Traditional Black-Box AI Card */}
        {recessionMode && (
          <div className="glass-card-cred slide-up" style={{ flex: 1, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '4px', background: isCrashed ? 'var(--danger)' : 'var(--text-muted)' }}></div>
            <p style={{ color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', fontSize: '0.8rem', fontWeight: 600 }}>Traditional Black-Box ML</p>
            <div className={`score-big ${isCrashed ? 'danger' : ''}`} style={{ margin: '2rem 0', color: isCrashed ? 'var(--danger)' : 'var(--text-muted)' }}>
              {xgboost_score}
            </div>
            <p style={{ color: isCrashed ? 'var(--danger)' : 'var(--text-muted)', fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              {isCrashed ? <><ShieldAlert size={16}/> Collapsed due to drift</> : "Simulating..."}
            </p>
          </div>
        )}
      </div>

      {/* ── PRODUCT DECISION ── */}
      <div className={decision === "DECLINE" ? "glass-card-danger" : "glass-card-cred"} style={{ textAlign: 'center', marginBottom: '3rem', padding: '3rem' }}>
        <h2 style={{ fontFamily: 'Outfit', fontSize: '2.5rem', marginBottom: '1rem', color: decision === "DECLINE" ? 'var(--danger)' : 'var(--text-primary)' }}>
          {decision === "STANDARD" && "Approved: Standard Line"}
          {decision === "NANO_CREDIT" && "Approved: Nano Line"}
          {decision === "DECLINE" && "Application Declined"}
        </h2>
        
        {product && (
          <>
            <div style={{ fontFamily: 'Outfit', fontSize: '4rem', fontWeight: 900, margin: '1rem 0', color: 'var(--neon-mint)', letterSpacing: '-2px' }}>
              ₹{product.amount.toLocaleString()}
            </div>
            {product.insurance && (
              <p style={{ color: 'var(--text-muted)', display: 'inline-block', border: '1px solid var(--border-subtle)', padding: '0.5rem 1rem', borderRadius: '50px', fontSize: '0.9rem' }}>
                Includes bundled payment protection
              </p>
            )}
          </>
        )}
      </div>

      {/* ── FORENSICS TOGGLE ── */}
      <button className="btn-outline" onClick={() => setShowForensics(!showForensics)} style={{ width: '100%', marginBottom: '3rem' }}>
        {showForensics ? "Hide Causal Forensics" : "View Causal Forensics"}
      </button>

      {showForensics && (
        <div className="slide-up">
          
          {/* Ignored Spurious Features */}
          <div className="glass-card-cred" style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--danger)', marginBottom: '1.5rem' }}>
              <ShieldAlert size={24} /> Ignored Spurious Bias
            </h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', fontSize: '0.95rem', lineHeight: 1.5 }}>
              Standard models exploit these correlations. Our causal engine proved they are spurious and intentionally discarded them to guarantee fairness.
            </p>
            <div style={{ display: 'grid', gap: '1rem' }}>
              {ignored_features?.map(f => (
                <div key={f.name} style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger-glow)', padding: '1.2rem', borderRadius: '12px' }}>
                  <strong style={{ color: 'var(--text-primary)', fontFamily: 'Outfit', fontSize: '1.1rem' }}>{f.name}</strong>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '6px' }}>{f.description}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Used Features */}
          <div className="glass-card-cred" style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--neon-mint)', marginBottom: '2rem' }}>
              <CheckCircle2 size={24} /> Verified Causal Drivers
            </h3>
            {Object.entries(contributions || {}).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1])).map(([feat, val]) => (
              <div key={feat} style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.95rem', marginBottom: '8px', color: 'var(--text-primary)' }}>
                  <span style={{ fontFamily: 'Inter' }}>{feat}</span>
                  <span style={{ color: val > 0 ? 'var(--danger)' : 'var(--neon-mint)', fontWeight: 600 }}>{val > 0 ? 'Risk Increasing' : 'Risk Reducing'}</span>
                </div>
                <div className="progress-container">
                  <div className="progress-bar" style={{ 
                    width: `${Math.min(100, Math.abs(val) * 30)}%`, 
                    background: val > 0 ? 'var(--danger)' : 'var(--neon-mint)'
                  }}></div>
                </div>
              </div>
            ))}
          </div>

          {/* ILF Timeline */}
          {ilf && (
            <div className="glass-card-cred" style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-primary)', marginBottom: '1.5rem' }}>
                <BrainCircuit size={24} /> Behavioral Biometrics
              </h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '2.5rem', fontSize: '0.95rem' }}>
                Sub-millisecond reaction tracking verifies cognitive intent and prevents brute-forcing.
              </p>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', height: '180px', padding: '1rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
                {ilf.latencies_sec.map((lat, i) => {
                  const heightPct = Math.min(100, (lat / 10) * 100);
                  const isSuspicious = lat < 1.0 || lat > 6.0;
                  const color = isSuspicious ? 'var(--danger)' : 'var(--neon-mint)';
                  
                  return (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontFamily: 'Outfit' }}>{lat.toFixed(2)}s</span>
                      <div style={{ width: '2px', height: `${heightPct}%`, background: color, position: 'relative' }}>
                        <div style={{ position: 'absolute', top: 0, left: '-4px', width: '10px', height: '10px', borderRadius: '50%', background: color, boxShadow: `0 0 10px ${color}` }}></div>
                      </div>
                      <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>Q{i+1}</span>
                    </div>
                  );
                })}
              </div>
              
              <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                <div style={{ 
                  display: 'inline-block', 
                  border: `1px solid ${ilf.reliability_label === 'High' ? 'var(--neon-mint)' : 'var(--danger)'}`,
                  color: ilf.reliability_label === 'High' ? 'var(--neon-mint)' : 'var(--danger)',
                  padding: '0.8rem 1.5rem', 
                  borderRadius: '50px', 
                  fontFamily: 'Outfit',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  letterSpacing: '1px',
                  textTransform: 'uppercase'
                }}>
                  {ilf.reliability_pct}% Reliability — {ilf.reliability_label}
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      <button className="btn-primary" onClick={() => navigate('/')} style={{ marginTop: '1rem' }}>
        Reset Engine
      </button>
    </div>
  );
}
