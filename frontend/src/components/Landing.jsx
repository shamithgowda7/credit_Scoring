import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const API = 'http://127.0.0.1:8000';
const STATS = [
  { value: 856, suffix: '', label: 'Recession AUC ×1000' },
  { value: 500, suffix: 'ms', label: 'Decision Latency' },
  { value: 6, suffix: '', label: 'Causal Features' },
  { value: 0, suffix: '%', label: 'Protected Attr. Used' },
];
const FEATURES = [
  { icon: '🧬', bg: 'var(--accent-dim)', title: 'Causal AI Scoring', desc: 'Only causally-valid features survive. Spurious correlations are automatically frozen before they cause harm.' },
  { icon: '🧠', bg: 'var(--blue-dim)', title: 'Behavioral Biometrics', desc: 'Instinct-Latency Framework captures response patterns invisible to traditional models.' },
  { icon: '🕸️', bg: 'var(--purple-dim)', title: 'Knowledge Graph', desc: 'Living graph of borrower, employer & merchant relationships compounds intelligence with every loan.' },
  { icon: '🛡️', bg: 'var(--amber-dim)', title: 'Recession-Proof', desc: 'AUC degrades <0.5% under simulated recession. Black-box models collapse by 8-15%.' },
  { icon: '🔍', bg: 'var(--rose-dim)', title: 'Forensic Explainability', desc: 'Every decision comes with plain-language factor breakdown satisfying RBI, DPDP & EU AI Act.' },
  { icon: '📈', bg: 'var(--accent-dim)', title: 'Self-Improving', desc: 'Repayment-under-duress signals, feature labs, and dynamic thresholds create a system that gets smarter.' },
];

export default function Landing() {
  const nav = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', bank_name: '', message: '' });
  const [sent, setSent] = useState(false);
  const [counts, setCounts] = useState(STATS.map(() => 0));
  const statsRef = useRef(null);
  const animated = useRef(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !animated.current) {
        animated.current = true;
        STATS.forEach((s, i) => {
          const dur = 1200;
          const start = performance.now();
          const tick = (now) => {
            const p = Math.min((now - start) / dur, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            setCounts(prev => { const n = [...prev]; n[i] = Math.round(s.value * eased); return n; });
            if (p < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        });
      }
    }, { threshold: 0.3 });
    if (statsRef.current) obs.observe(statsRef.current);
    return () => obs.disconnect();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    try { await fetch(`${API}/leads`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) }); setSent(true); } catch {}
  };

  return (
    <div className="landing">
      <nav className={`landing-nav${scrolled ? ' scrolled' : ''}`}>
        <div className="brand">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="12" stroke="#00e68a" strokeWidth="2.5"/><path d="M10 14l3 3 5-6" stroke="#00e68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          CausalScore
        </div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#contact">Contact</a>
          <button className="btn btn-primary btn-sm" onClick={() => nav('/dashboard')}>Dashboard →</button>
        </div>
      </nav>

      <section className="landing-hero">
        <h1 className="animate-in">Credit scoring that survives a <span className="gradient-text">recession</span></h1>
        <p className="subtitle animate-in-1">Causal AI engine that transforms thin-file individuals into bankable customers — explainable, self-improving, and stable under economic shocks.</p>
        <div style={{ display: 'flex', gap: 12 }} className="animate-in-2">
          <button className="btn btn-primary" onClick={() => nav('/assess')}>Try Live Demo</button>
          <button className="btn btn-secondary" onClick={() => nav('/dashboard')}>View Dashboard</button>
        </div>
        <div className="landing-stats animate-in-3" ref={statsRef}>
          {STATS.map((s, i) => (
            <div className="landing-stat" key={i}>
              <div className="num">{counts[i]}{s.suffix}</div>
              <div className="label">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" id="features">
        <h2>How it works</h2>
        <p className="section-sub">A scoring engine built on structural causal models, not pattern-matching. Every feature earns its place through causal validation.</p>
        <div className="features-grid">
          {FEATURES.map((f, i) => (
            <div className={`feature-card animate-in-${Math.min(i, 4)}`} key={i}>
              <div className="icon" style={{ background: f.bg }}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-cta" id="contact">
        <div className="cta-card card">
          <h2 style={{ marginBottom: 8 }}>Ready to deploy?</h2>
          <p style={{ color: 'var(--text-1)', marginBottom: 24, fontSize: '0.95rem' }}>Get the recession-proof scoring API for your institution.</p>
          {sent ? (
            <div style={{ padding: 20, color: 'var(--accent)' }}>✓ Thank you! We'll be in touch shortly.</div>
          ) : (
            <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div><label className="field-label">Name</label><input className="input" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} required /></div>
                <div><label className="field-label">Email</label><input className="input" type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} required /></div>
              </div>
              <div><label className="field-label">Institution</label><input className="input" value={form.bank_name} onChange={e => setForm(p => ({ ...p, bank_name: e.target.value }))} required /></div>
              <div><label className="field-label">Message</label><textarea className="input" rows={3} value={form.message} onChange={e => setForm(p => ({ ...p, message: e.target.value }))} /></div>
              <button className="btn btn-primary" type="submit" style={{ alignSelf: 'flex-end' }}>Send Inquiry</button>
            </form>
          )}
        </div>
      </section>

      <footer className="landing-footer">
        <span>© 2026 CausalScore. Recession-Proof Credit Intelligence.</span>
        <div style={{ display: 'flex', gap: 16 }}>
          <a href="#features" style={{ color: 'var(--text-2)' }}>Features</a>
          <a href="#contact" style={{ color: 'var(--text-2)' }}>Contact</a>
        </div>
      </footer>
    </div>
  );
}
