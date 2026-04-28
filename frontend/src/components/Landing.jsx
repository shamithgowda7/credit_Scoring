import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, BrainCircuit, ActivitySquare, TrendingDown, ArrowRight, Play, Send, ChevronDown } from 'lucide-react';

/* ── Animated Counter Hook ── */
function useCounter(end, duration = 2000, trigger = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!trigger) return;
    let start = 0;
    const increment = end / (duration / 16);
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) { setCount(end); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [trigger, end, duration]);
  return count;
}

/* ── Scroll Reveal Hook ── */
function useScrollReveal() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, visible];
}

export default function Landing() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ name: '', email: '', bank_name: '', message: '' });
  const [formStatus, setFormStatus] = useState(null);

  const [problemRef, problemVisible] = useScrollReveal();
  const [solutionRef, solutionVisible] = useScrollReveal();
  const [videoRef, videoVisible] = useScrollReveal();
  const [contactRef, contactVisible] = useScrollReveal();

  const stat1 = useCounter(73, 2000, problemVisible);
  const stat2 = useCounter(4, 1500, problemVisible);
  const stat3 = useCounter(98, 2000, solutionVisible);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://127.0.0.1:8000/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      setFormStatus(data.message);
      setFormData({ name: '', email: '', bank_name: '', message: '' });
    } catch { setFormStatus("Could not submit. Please try again."); }
  };

  const sectionStyle = (visible) => ({
    opacity: visible ? 1 : 0,
    transform: visible ? 'translateY(0)' : 'translateY(60px)',
    transition: 'all 0.9s cubic-bezier(0.16, 1, 0.3, 1)',
  });

  return (
    <div style={{ overflow: 'hidden' }}>

      {/* ── NAV BAR ── */}
      <nav style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100, padding: '1.5rem 3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backdropFilter: 'blur(20px)', background: 'rgba(5,5,5,0.8)', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ fontFamily: 'Outfit', fontWeight: 800, fontSize: '1.4rem', letterSpacing: '-1px' }}>
          <span style={{ color: 'var(--neon-mint)' }}>Future</span>Bank
        </div>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
          <button className="btn-outline" onClick={() => navigate('/dashboard')} style={{ padding: '0.6rem 1.5rem', fontSize: '0.9rem' }}>
            Bank Dashboard
          </button>
          <button className="btn-primary" onClick={() => navigate('/assess')} style={{ padding: '0.6rem 1.5rem', fontSize: '0.9rem', width: 'auto' }}>
            Try Demo
          </button>
        </div>
      </nav>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 1: HERO
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '6rem 2rem 4rem', position: 'relative' }}>
        {/* Subtle radial glow */}
        <div style={{ position: 'absolute', top: '-20%', left: '50%', transform: 'translateX(-50%)', width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(0,255,157,0.06) 0%, transparent 70%)', pointerEvents: 'none' }}></div>

        <div className="slide-up" style={{ maxWidth: '900px' }}>
          <p style={{ color: 'var(--neon-mint)', letterSpacing: '4px', textTransform: 'uppercase', fontSize: '0.85rem', fontWeight: 600, marginBottom: '2rem' }}>
            B2B Credit Infrastructure
          </p>
          <h1 style={{ fontFamily: 'Outfit', fontSize: 'clamp(3rem, 7vw, 5.5rem)', fontWeight: 900, lineHeight: 1.05, letterSpacing: '-3px', marginBottom: '2rem' }}>
            Credit scoring<br/>that doesn't break<br/>in a <span className="highlight">recession.</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.3rem', maxWidth: '600px', margin: '0 auto 3rem', lineHeight: 1.6 }}>
            The world's first causal AI credit engine. Recession-tested. Bias-free. Built for banks that refuse to gamble on correlations.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={() => navigate('/assess')} style={{ width: 'auto', padding: '1.2rem 2.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
              Try the Demo <ArrowRight size={18}/>
            </button>
            <a href="#contact" style={{ textDecoration: 'none' }}>
              <button className="btn-outline" style={{ padding: '1.2rem 2.5rem' }}>
                Request Access
              </button>
            </a>
          </div>
        </div>

        <a href="#problem" style={{ position: 'absolute', bottom: '2rem', color: 'var(--text-muted)', textDecoration: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', letterSpacing: '2px', textTransform: 'uppercase' }}>Scroll</span>
          <ChevronDown size={20} style={{ animation: 'bounce 2s infinite' }}/>
        </a>

        <style>{`@keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(8px)} }`}</style>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 2: THE PROBLEM
      ══════════════════════════════════════════════════════════════════════ */}
      <section id="problem" ref={problemRef} style={{ padding: '8rem 2rem', maxWidth: '1100px', margin: '0 auto', ...sectionStyle(problemVisible) }}>
        <p style={{ color: 'var(--danger)', letterSpacing: '3px', textTransform: 'uppercase', fontSize: '0.85rem', fontWeight: 600, marginBottom: '1.5rem' }}>
          The Problem
        </p>
        <h2 style={{ fontFamily: 'Outfit', fontSize: '3rem', fontWeight: 800, lineHeight: 1.15, letterSpacing: '-1.5px', marginBottom: '3rem' }}>
          Traditional credit models are <span style={{ color: 'var(--danger)' }}>ticking time bombs.</span>
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '2rem', marginBottom: '3rem' }}>
          <div className="glass-card-cred" style={{ textAlign: 'center', padding: '2.5rem' }}>
            <div style={{ fontFamily: 'Outfit', fontSize: '4rem', fontWeight: 900, color: 'var(--danger)', lineHeight: 1 }}>{stat1}%</div>
            <p style={{ color: 'var(--text-muted)', marginTop: '1rem', lineHeight: 1.4 }}>of black-box models collapse under macroeconomic stress</p>
          </div>
          <div className="glass-card-cred" style={{ textAlign: 'center', padding: '2.5rem' }}>
            <div style={{ fontFamily: 'Outfit', fontSize: '4rem', fontWeight: 900, color: 'var(--danger)', lineHeight: 1 }}>{stat2}x</div>
            <p style={{ color: 'var(--text-muted)', marginTop: '1rem', lineHeight: 1.4 }}>increase in NPAs when spurious features drift during a recession</p>
          </div>
          <div className="glass-card-cred" style={{ textAlign: 'center', padding: '2.5rem' }}>
            <TrendingDown size={48} style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}/>
            <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: 1.4 }}>Features like "dark mode user" and "social media score" create invisible bias that regulators can't audit</p>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 3: OUR SOLUTION
      ══════════════════════════════════════════════════════════════════════ */}
      <section ref={solutionRef} style={{ padding: '8rem 2rem', maxWidth: '1100px', margin: '0 auto', ...sectionStyle(solutionVisible) }}>
        <p style={{ color: 'var(--neon-mint)', letterSpacing: '3px', textTransform: 'uppercase', fontSize: '0.85rem', fontWeight: 600, marginBottom: '1.5rem' }}>
          Our Solution
        </p>
        <h2 style={{ fontFamily: 'Outfit', fontSize: '3rem', fontWeight: 800, lineHeight: 1.15, letterSpacing: '-1.5px', marginBottom: '1rem' }}>
          We replaced correlation with <span className="highlight">causation.</span>
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.15rem', maxWidth: '700px', marginBottom: '4rem', lineHeight: 1.6 }}>
          Our engine uses a Structural Causal Model to distinguish features that actually <em>cause</em> default from features that merely correlate with it. The result is a credit score that holds up in any economy.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
          <div className="glass-card-cred" style={{ borderTop: '3px solid var(--neon-mint)' }}>
            <BrainCircuit size={32} color="var(--neon-mint)" style={{ marginBottom: '1.5rem' }}/>
            <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', marginBottom: '1rem' }}>Causal AI Engine</h3>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Uses Directed Acyclic Graphs (DAGs) to identify true causal drivers of default. Not correlations — actual causes. Our model achieved <strong style={{ color: 'var(--neon-mint)' }}>{stat3}% stability</strong> during simulated recession stress tests while black-box models collapsed.
            </p>
          </div>
          <div className="glass-card-cred" style={{ borderTop: '3px solid var(--neon-mint)' }}>
            <ShieldCheck size={32} color="var(--neon-mint)" style={{ marginBottom: '1.5rem' }}/>
            <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', marginBottom: '1rem' }}>ILF Behavioral Biometrics</h3>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Our patented Inverse Latency Function uses sub-millisecond behavioral tracking to verify borrower intent. It detects fraud, automation, and dishonesty — without asking a single extra question.
            </p>
          </div>
          <div className="glass-card-cred" style={{ borderTop: '3px solid var(--neon-mint)' }}>
            <ActivitySquare size={32} color="var(--neon-mint)" style={{ marginBottom: '1.5rem' }}/>
            <h3 style={{ fontFamily: 'Outfit', fontSize: '1.5rem', marginBottom: '1rem' }}>Recession-Proof by Design</h3>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>
              We stress-tested our models against real recession regime shifts. Where traditional ML AUC drops to 0.41, our Causal Engine holds at 0.86. Your NPAs don't spike when the market dips.
            </p>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 4: PRODUCT VIDEO
      ══════════════════════════════════════════════════════════════════════ */}
      <section ref={videoRef} style={{ padding: '8rem 2rem', maxWidth: '900px', margin: '0 auto', ...sectionStyle(videoVisible) }}>
        <p style={{ color: 'var(--neon-mint)', letterSpacing: '3px', textTransform: 'uppercase', fontSize: '0.85rem', fontWeight: 600, marginBottom: '1.5rem', textAlign: 'center' }}>
          See It In Action
        </p>
        <h2 style={{ fontFamily: 'Outfit', fontSize: '3rem', fontWeight: 800, textAlign: 'center', letterSpacing: '-1.5px', marginBottom: '3rem' }}>
          Watch the product walkthrough.
        </h2>

        {/* Video Embed Placeholder */}
        <div style={{ position: 'relative', aspectRatio: '16/9', background: 'var(--bg-card)', borderRadius: '20px', border: '1px solid var(--border-subtle)', overflow: 'hidden', cursor: 'pointer' }}
          onClick={() => navigate('/assess')}
        >
          {/* Replace the div below with <iframe src="YOUR_YOUTUBE_OR_LOOM_URL" .../> when you have a real video */}
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '1.5rem', background: 'radial-gradient(circle, rgba(0,255,157,0.05) 0%, transparent 60%)' }}>
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(0,255,157,0.15)', border: '2px solid var(--neon-mint)', display: 'flex', justifyContent: 'center', alignItems: 'center', transition: 'all 0.3s ease' }}>
              <Play size={32} color="var(--neon-mint)" style={{ marginLeft: '4px' }}/>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Click to experience the live demo</p>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 5: CONTACT / CTA
      ══════════════════════════════════════════════════════════════════════ */}
      <section id="contact" ref={contactRef} style={{ padding: '8rem 2rem', maxWidth: '700px', margin: '0 auto', ...sectionStyle(contactVisible) }}>
        <p style={{ color: 'var(--neon-mint)', letterSpacing: '3px', textTransform: 'uppercase', fontSize: '0.85rem', fontWeight: 600, marginBottom: '1.5rem', textAlign: 'center' }}>
          Get Started
        </p>
        <h2 style={{ fontFamily: 'Outfit', fontSize: '3rem', fontWeight: 800, textAlign: 'center', letterSpacing: '-1.5px', marginBottom: '1rem' }}>
          Ready to future-proof your lending?
        </h2>
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginBottom: '3rem', fontSize: '1.1rem' }}>
          Leave your details below and our team will schedule a private demo for your institution.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <input placeholder="Your Name" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} required
              style={{ padding: '1.2rem', borderRadius: '14px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'white', fontSize: '1rem', outline: 'none', fontFamily: 'Inter', transition: 'border-color 0.3s' }}
              onFocus={e => e.target.style.borderColor = 'var(--neon-mint)'} onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
            />
            <input placeholder="Work Email" type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} required
              style={{ padding: '1.2rem', borderRadius: '14px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'white', fontSize: '1rem', outline: 'none', fontFamily: 'Inter', transition: 'border-color 0.3s' }}
              onFocus={e => e.target.style.borderColor = 'var(--neon-mint)'} onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
            />
          </div>
          <input placeholder="Bank / Institution Name" value={formData.bank_name} onChange={e => setFormData({ ...formData, bank_name: e.target.value })} required
            style={{ padding: '1.2rem', borderRadius: '14px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'white', fontSize: '1rem', outline: 'none', fontFamily: 'Inter', transition: 'border-color 0.3s' }}
            onFocus={e => e.target.style.borderColor = 'var(--neon-mint)'} onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
          />
          <textarea placeholder="Tell us about your lending volume and challenges..." rows={4} value={formData.message} onChange={e => setFormData({ ...formData, message: e.target.value })}
            style={{ padding: '1.2rem', borderRadius: '14px', background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'white', fontSize: '1rem', outline: 'none', fontFamily: 'Inter', resize: 'vertical', transition: 'border-color 0.3s' }}
            onFocus={e => e.target.style.borderColor = 'var(--neon-mint)'} onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
          />
          <button type="submit" className="btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <Send size={18}/> Request Access
          </button>
          {formStatus && (
            <p style={{ textAlign: 'center', color: 'var(--neon-mint)', marginTop: '1rem' }}>{formStatus}</p>
          )}
        </form>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ padding: '3rem 2rem', textAlign: 'center', borderTop: '1px solid var(--border-subtle)' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          FutureBank Credit Engine &mdash; Causal AI for Recession-Proof Lending
        </p>
      </footer>

    </div>
  );
}
