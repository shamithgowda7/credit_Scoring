import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function Welcome() {
  const navigate = useNavigate();
  const [consent, setConsent] = useState(false);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');

  useEffect(() => {
    fetch('http://127.0.0.1:8000/demo-users')
      .then(res => res.json())
      .then(data => {
        if (data.users) {
          setUsers(data.users);
          setSelectedUserId(data.users[0].id.toString());
        }
      })
      .catch(err => console.error("Could not load demo users", err));
  }, []);

  const handleStart = () => {
    const user = users.find(u => u.id.toString() === selectedUserId);
    sessionStorage.setItem('selectedUser', JSON.stringify(user));
    navigate('/assess/questions');
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
        
        {users.length > 0 && (
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
          disabled={!consent || users.length === 0} 
          onClick={handleStart}
        >
          Begin Analysis
        </button>
      </div>
      
    </div>
  );
}
