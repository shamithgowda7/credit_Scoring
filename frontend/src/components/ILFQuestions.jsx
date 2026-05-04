import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const API = 'http://127.0.0.1:8000';

export default function ILFQuestions() {
  const { state } = useLocation();
  const nav = useNavigate();
  const [question, setQuestion] = useState(null);
  const [options, setOptions] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [qNum, setQNum] = useState(1);
  const startTime = useRef(performance.now());
  const latencies = useRef([]);

  const sessionId = state?.sessionId;
  const maxQ = 8;

  useEffect(() => {
    if (!sessionId) { nav('/assess'); return; }
    if (state?.firstResult?.status === 'ASK_QUESTION') {
      setQuestion(state.firstResult.question_text);
      setOptions(state.firstResult.options || []);
      startTime.current = performance.now();
    }
  }, []);

  const submitAnswer = async (answer) => {
    const latency = (performance.now() - startTime.current) / 1000;
    latencies.current.push(latency);
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API}/submit-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question, answer, response_latency_sec: latency }),
      });
      const data = await res.json();
      const result = data.result;

      setHistory(prev => [...prev, { q: question, a: answer, latency: latency.toFixed(1) }]);

      if (result?.status === 'ASK_QUESTION') {
        setQuestion(result.question_text);
        setOptions(result.options || []);
        setQNum(q => q + 1);
        startTime.current = performance.now();
      } else if (result?.status === 'CONFIDENT_EXTRACTION') {
        nav('/assess/processing', {
          state: {
            sessionId, features: result.features, confidence: result.confidence,
            scoreResult: data.score_result, latencies: latencies.current,
            history: [...history, { q: question, a: answer }], name: state?.name,
          },
        });
      }
    } catch (e) {
      setError('Connection failed. Retrying...');
    } finally { setLoading(false); }
  };

  if (!sessionId) return null;

  return (
    <div className="assess-page">
      <div className="step-progress">
        {Array.from({ length: maxQ }).map((_, i) => (
          <div key={i} className={`step-dot${i < qNum - 1 ? ' done' : i === qNum - 1 ? ' current' : ''}`} />
        ))}
      </div>

      <div style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-2)', marginBottom: 24 }}>
        Question {qNum} of {maxQ} • {state?.llmMode === 'gemini' ? '🧠 Gemini AI' : '🤖 Mock Mode'}
      </div>

      {loading ? (
        <div className="card animate-in" style={{ textAlign: 'center', padding: 40 }}>
          <div className="skeleton" style={{ width: '80%', height: 20, margin: '0 auto 12px' }} />
          <div className="skeleton" style={{ width: '60%', height: 16, margin: '0 auto' }} />
        </div>
      ) : error ? (
        <div className="card" style={{ textAlign: 'center', padding: 24, borderColor: 'var(--rose)' }}>
          <p style={{ color: 'var(--rose)', marginBottom: 12 }}>{error}</p>
          <button className="btn btn-secondary btn-sm" onClick={() => setError(null)}>Retry</button>
        </div>
      ) : question ? (
        <div className="card question-card animate-in">
          <h2>{question}</h2>
          <div className="options-grid">
            {options.map((opt, i) => (
              <button key={i} className="option-btn" onClick={() => submitAnswer(opt)}>
                {opt}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {history.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="section-title" style={{ fontSize: '0.82rem' }}>Interview Recap</div>
          {history.map((h, i) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: '0.82rem' }}>
              <div style={{ color: 'var(--text-1)' }}>Q{i + 1}: {h.q}</div>
              <div style={{ fontWeight: 600, marginTop: 2 }}>→ {h.a} <span style={{ color: 'var(--text-2)', fontWeight: 400 }}>({h.latency}s)</span></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
