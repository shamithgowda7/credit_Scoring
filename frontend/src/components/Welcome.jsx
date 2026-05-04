import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API = 'http://127.0.0.1:8000';
const PERSONAS = [
  { id: 1, name: 'Rajesh Kumar', context: 'Rajesh is a delivery driver earning ₹18,000/month via Zomato/Swiggy. His income fluctuates with seasons. He sends ₹5,000 home monthly. He has one dependent child.', tier: 'Medium' },
  { id: 2, name: 'Meera Devi', context: 'Meera runs a small tailoring business in Jaipur earning ₹20,000-30,000/month. She has a pending ₹50,000 loan from a local lender. Business peaks during festivals.', tier: 'Medium' },
  { id: 3, name: 'Amit Shah', context: 'Amit is a salaried TechCorp software engineer earning ₹85,000/month. He has an EMI of ₹15,000 and invests ₹20,000 monthly in SIPs. Very stable employment.', tier: 'Low' },
  { id: 4, name: 'Priya Nair', context: 'Priya is a freelance graphic designer earning ₹25,000-60,000/month. Income is highly variable. She recently lost a major client and has 2 months of savings.', tier: 'High' },
];

export default function Welcome() {
  const nav = useNavigate();
  const [mode, setMode] = useState('demo');
  const [personaIdx, setPersonaIdx] = useState(0);
  const [customName, setCustomName] = useState('');
  const [customContext, setCustomContext] = useState('');
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);

  const persona = PERSONAS[personaIdx];
  const name = mode === 'demo' ? persona.name : customName;
  const context = mode === 'demo' ? persona.context : customContext;
  const canStart = consent && name.trim() && context.trim();

  const start = async () => {
    if (!canStart) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/start-assessment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, bank_context: context }),
      });
      const data = await res.json();
      if (data.session_id) {
        nav('/assess/questions', { state: { sessionId: data.session_id, firstResult: data.result, name, context, llmMode: data.llm_mode } });
      }
    } catch (e) {
      alert('Failed to start assessment. Is the API running?');
    } finally { setLoading(false); }
  };

  return (
    <div className="assess-page">
      <div className="assess-header animate-in">
        <h1>Credit Assessment</h1>
        <p>Run a behavioral interview to extract causal credit features</p>
      </div>

      <div className="mode-cards animate-in-1">
        <div className={`mode-card${mode === 'demo' ? ' selected' : ''}`} onClick={() => setMode('demo')}>
          <div style={{ fontSize: '1.5rem' }}>👤</div>
          <h3>Demo Persona</h3>
          <p>Use a pre-built borrower profile</p>
        </div>
        <div className={`mode-card${mode === 'custom' ? ' selected' : ''}`} onClick={() => setMode('custom')}>
          <div style={{ fontSize: '1.5rem' }}>✏️</div>
          <h3>Custom Applicant</h3>
          <p>Enter your own details</p>
        </div>
      </div>

      <div className="card animate-in-2" style={{ marginBottom: 16 }}>
        {mode === 'demo' ? (
          <>
            <label className="field-label">Select Persona</label>
            <select className="persona-select" value={personaIdx} onChange={e => setPersonaIdx(Number(e.target.value))}>
              {PERSONAS.map((p, i) => <option key={i} value={i}>{p.name} — {p.tier} Risk</option>)}
            </select>
            <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-2)', borderRadius: 'var(--radius-sm)', fontSize: '0.88rem', color: 'var(--text-1)', lineHeight: 1.6 }}>
              {persona.context}
            </div>
          </>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div><label className="field-label">Applicant Name</label><input className="input" value={customName} onChange={e => setCustomName(e.target.value)} placeholder="e.g. Rajesh Kumar" /></div>
            <div><label className="field-label">Financial Context</label><textarea className="input" rows={4} value={customContext} onChange={e => setCustomContext(e.target.value)} placeholder="Describe occupation, income, expenses, dependents..." /></div>
            <div style={{ display: 'flex', gap: 8 }}>
              {PERSONAS.map((p, i) => (
                <button key={i} className="btn btn-ghost btn-sm" onClick={() => { setCustomName(p.name); setCustomContext(p.context); }}>
                  Use {p.name.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <label className="checkbox-wrap animate-in-3" style={{ marginBottom: 20 }}>
        <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
        <span style={{ fontSize: '0.85rem', color: 'var(--text-1)' }}>I consent to behavioral analysis for credit assessment. Response timing will be recorded. No raw data leaves this session.</span>
      </label>

      <button className={`btn btn-primary animate-in-4`} onClick={start} disabled={!canStart || loading} style={{ width: '100%', justifyContent: 'center' }}>
        {loading ? 'Starting...' : 'Begin Assessment →'}
      </button>
    </div>
  );
}
