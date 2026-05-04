import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const STEPS = [
  { label: 'Extracting causal features', desc: 'LLM analyzed responses to derive income, stability, and risk signals' },
  { label: 'Computing ILF reliability', desc: 'Behavioral biometrics scored response patterns and catch-trial results' },
  { label: 'Querying Knowledge Graph', desc: 'Checking borrower network for employer risk and community context' },
  { label: 'Running Causal LR model', desc: 'Only causally-valid features enter the scoring equation' },
  { label: 'Generating decision', desc: 'Score mapped to decision tier with dynamic thresholds' },
];

export default function Processing() {
  const { state } = useLocation();
  const nav = useNavigate();
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!state?.sessionId) { nav('/assess'); return; }
    const timer = setInterval(() => {
      setStep(s => {
        if (s >= STEPS.length - 1) {
          clearInterval(timer);
          setTimeout(() => nav('/assess/results', { state }), 600);
          return s;
        }
        return s + 1;
      });
    }, 700);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="processing-page">
      <h2 className="animate-in" style={{ fontSize: '1.4rem', fontWeight: 700 }}>Analyzing Assessment</h2>
      <p className="animate-in-1" style={{ color: 'var(--text-1)', marginTop: 8 }}>{state?.name || 'Applicant'}</p>

      <div className="progress-bar animate-in-2" style={{ width: '100%', maxWidth: 400, marginTop: 24 }}>
        <div className="progress-fill" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
      </div>

      <div className="processing-steps animate-in-3">
        {STEPS.map((s, i) => (
          <div key={i} className={`proc-step${i <= step ? ' done' : ''}`}>
            <div className="step-icon">{i <= step ? '✓' : i === step + 1 ? '...' : ''}</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{s.label}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-1)' }}>{s.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
