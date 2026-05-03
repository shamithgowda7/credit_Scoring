import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const CONTEXT_TEMPLATES = [
  {
    label: "Gig Worker",
    icon: "🏍️",
    text: "Ravi is a 28-year-old delivery driver working across multiple gig platforms. His monthly income ranges from ₹12,000 to ₹35,000 depending on demand. He pays rent and utilities but occasionally misses payment deadlines during slow months. He has no formal employment contract and no employer-provided benefits. He recently took a small personal loan to repair his vehicle. He has one dependent (elderly mother)."
  },
  {
    label: "Small Business",
    icon: "🏪",
    text: "Meera runs a small tailoring business from her home in a semi-urban area. She earns approximately ₹20,000-₹30,000 monthly with seasonal peaks during festivals. She has a savings account with ₹45,000 and pays utility bills consistently. She has an outstanding micro-loan of ₹15,000 from a local cooperative. Her husband works as a daily wage laborer earning ₹8,000/month. Two school-aged children."
  },
  {
    label: "Salaried Employee",
    icon: "💼",
    text: "Arjun is a 35-year-old IT professional earning ₹85,000/month with annual bonuses. He has a home loan EMI of ₹22,000 and a car loan EMI of ₹12,000. He pays all bills on time via auto-debit. He has ₹3,00,000 in savings and ₹2,00,000 in mutual funds. He was recently promoted and his income has been stable for 4 years. No dependents other than spouse who also works."
  }
];

export default function Welcome() {
  const navigate = useNavigate();
  const [consent, setConsent] = useState(false);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [mode, setMode] = useState('demo');
  const [customUser, setCustomUser] = useState({
    name: '',
    bankContext: ''
  });
  const [isStarting, setIsStarting] = useState(false);
  const [llmStatus, setLlmStatus] = useState({ available: false, mode: 'checking' });

  useEffect(() => {
    // Load demo users
    fetch('http://127.0.0.1:8000/demo-users')
      .then(res => res.json())
      .then(data => {
        if (data.users) {
          setUsers(data.users);
          setSelectedUserId(data.users[0].id.toString());
        }
      })
      .catch(err => console.error("Could not load demo users", err));

    // Check LLM availability
    fetch('http://127.0.0.1:8000/health')
      .then(res => res.json())
      .then(data => {
        setLlmStatus({
          available: data.llm_available || false,
          mode: data.llm_mode || 'mock'
        });
      })
      .catch(() => setLlmStatus({ available: false, mode: 'offline' }));
  }, []);

  const handleStart = async () => {
    if (mode === 'demo') {
      const user = users.find(u => u.id.toString() === selectedUserId);
      sessionStorage.setItem('selectedUser', JSON.stringify(user));
      sessionStorage.removeItem('llmSession');
      sessionStorage.removeItem('isLLMSession');
      sessionStorage.removeItem('preScored');
      navigate('/assess/questions');
    } else {
      setIsStarting(true);
      try {
        const res = await fetch('http://127.0.0.1:8000/start-assessment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: customUser.name || "Custom Applicant",
            bank_context: customUser.bankContext || "Applicant with no prior bank history."
          })
        });
        const data = await res.json();
        
        sessionStorage.setItem('llmSession', JSON.stringify({
          sessionId: data.session_id,
          name: customUser.name || "Custom Applicant"
        }));
        sessionStorage.setItem('nextQuestion', JSON.stringify(data.result));
        sessionStorage.removeItem('preScored');
        navigate('/assess/questions');
      } catch (err) {
        console.error("Failed to start assessment", err);
        setIsStarting(false);
      }
    }
  };

  const applyTemplate = (template) => {
    setCustomUser({
      ...customUser,
      bankContext: template.text
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '80vh', maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>

      <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2rem', fontFamily: 'Inter', fontSize: '0.9rem' }}>
        <ArrowLeft size={16}/> Back to Home
      </button>
      
      <div className="slide-up">
        <h1 className="hero-title">
          financial<br/>progress,<br/><span className="highlight">rewarded.</span>
        </h1>
        <p className="hero-sub" style={{ marginBottom: '4rem' }}>
          Experience the world's first recession-proof, causal AI credit engine.
        </p>
      </div>

      <div className="slide-up slide-up-delay-1" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        
        {/* Mode Toggle */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <button 
            onClick={() => setMode('demo')}
            style={{ flex: 1, padding: '0.8rem', background: mode === 'demo' ? 'var(--neon-mint)' : 'var(--bg-card)', color: mode === 'demo' ? '#000' : 'var(--text-muted)', border: '1px solid var(--border-subtle)', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}>
            Demo Persona
          </button>
          <button 
            onClick={() => setMode('custom')}
            style={{ flex: 1, padding: '0.8rem', background: mode === 'custom' ? 'var(--neon-mint)' : 'var(--bg-card)', color: mode === 'custom' ? '#000' : 'var(--text-muted)', border: '1px solid var(--border-subtle)', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}>
            Custom Applicant
          </button>
        </div>

        {mode === 'demo' && users.length > 0 && (
          <div>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.8rem', fontSize: '0.9rem', fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Select a persona
            </label>
            <select 
              className="custom-select" 
              value={selectedUserId} 
              onChange={(e) => setSelectedUserId(e.target.value)}
            >
              {users.map(u => (
                <option key={u.id} value={u.id}>
                  {u.name} — {u.risk_tier} Risk
                </option>
              ))}
            </select>
          </div>
        )}

        {mode === 'custom' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', padding: '1.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px solid var(--border-subtle)' }}>
            
            {/* LLM Status Indicator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
              <span style={{ 
                width: '8px', height: '8px', borderRadius: '50%', 
                background: llmStatus.mode === 'gemini' ? '#00FF9D' : llmStatus.mode === 'mock' ? '#F59E0B' : '#FF3B30',
                boxShadow: llmStatus.mode === 'gemini' ? '0 0 6px rgba(0,255,157,0.5)' : 'none'
              }}></span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>
                {llmStatus.mode === 'gemini' ? 'Gemini AI Active' : 
                 llmStatus.mode === 'mock' ? 'Demo Mode (No API Key)' : 
                 'Checking...'}
              </span>
            </div>

            <div>
              <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>Applicant Name</label>
              <input type="text" className="custom-select" placeholder="E.g. Ravi Kumar" value={customUser.name} onChange={e => setCustomUser({...customUser, name: e.target.value})} />
            </div>
            
            <div>
              <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>Bank Holding Context (Raw Text)</label>
              <textarea 
                className="custom-select" 
                style={{ height: '120px', resize: 'vertical' }}
                placeholder="Describe the applicant's financial situation, income sources, debts, and spending habits..."
                value={customUser.bankContext} 
                onChange={e => setCustomUser({...customUser, bankContext: e.target.value})} 
              />
            </div>

            {/* Quick-fill Templates */}
            <div>
              <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.8rem', fontSize: '0.75rem', letterSpacing: '1px', textTransform: 'uppercase' }}>
                Quick-fill Templates
              </label>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                {CONTEXT_TEMPLATES.map((t, i) => (
                  <button
                    key={i}
                    onClick={() => applyTemplate(t)}
                    style={{
                      flex: 1, padding: '0.7rem 0.5rem',
                      background: customUser.bankContext === t.text ? 'rgba(0,255,157,0.1)' : 'rgba(255,255,255,0.03)',
                      border: customUser.bankContext === t.text ? '1px solid var(--neon-mint)' : '1px solid var(--border-subtle)',
                      borderRadius: '10px', cursor: 'pointer',
                      transition: 'all 0.2s', textAlign: 'center',
                      color: 'var(--text-primary)', fontSize: '0.8rem',
                    }}
                  >
                    <div style={{ fontSize: '1.4rem', marginBottom: '4px' }}>{t.icon}</div>
                    <div style={{ fontWeight: 600, fontSize: '0.75rem' }}>{t.label}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <label className="custom-checkbox" style={{ padding: '1rem', background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border-subtle)' }}>
          <input 
            type="checkbox" 
            checked={consent} 
            onChange={(e) => setConsent(e.target.checked)} 
          />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.4 }}>
            I consent to behavioral tracking and understand my data will be processed using pure causal AI.
          </span>
        </label>

        <button 
          className="btn-primary" 
          disabled={!consent || (mode === 'demo' && users.length === 0) || isStarting} 
          onClick={handleStart}
        >
          {isStarting ? "Generating Persona..." : "Begin Analysis"}
        </button>
      </div>
      
    </div>
  );
}
