import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export default function ILFQuestions() {
  const navigate = useNavigate();
  const [questionData, setQuestionData] = useState(null);
  const [questionCount, setQuestionCount] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  
  // Tracking data
  const [answers, setAnswers] = useState([]);
  const [latencies, setLatencies] = useState([]);
  const [questionTexts, setQuestionTexts] = useState([]);
  const [qaHistory, setQaHistory] = useState([]);
  const renderTimeRef = useRef(0);
  const sessionStartRef = useRef(Date.now());

  // Detect LLM session vs demo mode
  const isLLMSession = !!sessionStorage.getItem('llmSession');

  useEffect(() => {
    if (isLLMSession) {
      const nextQ = JSON.parse(sessionStorage.getItem('nextQuestion'));
      setQuestionData(nextQ);
    } else {
      // Demo mode: use static ILF questions
      setQuestionData({
        status: "ASK_QUESTION",
        question_text: "I feel confident about handling unexpected expenses.",
        options: ["Agree", "Disagree"]
      });
    }
    renderTimeRef.current = performance.now();
    setIsVisible(true);
    setError(null);
  }, [questionCount]);

  const handleAnswer = async (answer) => {
    const clickTime = performance.now();
    const latencySec = (clickTime - renderTimeRef.current) / 1000;

    const newAnswers = [...answers, answer];
    const newLatencies = [...latencies, latencySec];
    const newQuestions = [...questionTexts, questionData?.question_text || ""];
    const newHistory = [...qaHistory, { q: questionData?.question_text, a: answer }];
    
    setAnswers(newAnswers);
    setLatencies(newLatencies);
    setQuestionTexts(newQuestions);
    setQaHistory(newHistory);

    setIsVisible(false);
    setIsLoading(true);
    setError(null);

    // ── Demo Mode: Static ILF Flow ──
    if (!isLLMSession) {
      setTimeout(() => {
        sessionStorage.setItem('ilfAnswers', JSON.stringify(newAnswers));
        sessionStorage.setItem('ilfLatencies', JSON.stringify(newLatencies));
        navigate('/assess/processing');
      }, 500);
      return;
    }

    // ── LLM Mode: Adaptive Loop ──
    const llmSession = JSON.parse(sessionStorage.getItem('llmSession'));

    try {
      const res = await fetch('http://127.0.0.1:8000/submit-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: llmSession.sessionId,
          question: questionData.question_text,
          answer: answer,
          response_latency_sec: latencySec,
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      const result = data.result;
      setRetryCount(0);

      if (result.status === "ASK_QUESTION") {
        sessionStorage.setItem('nextQuestion', JSON.stringify(result));
        setQuestionCount(prev => prev + 1);
        setIsLoading(false);

      } else if (result.status === "CONFIDENT_EXTRACTION") {
        // Store extracted features and pre-scored result
        const user = { ...llmSession, features: result.features };
        sessionStorage.setItem('selectedUser', JSON.stringify(user));
        
        // If the backend auto-scored, store it
        if (data.score_result) {
          sessionStorage.setItem('scoreResult', JSON.stringify(data.score_result));
          sessionStorage.setItem('preScored', 'true');
        }

        // Store ILF data for behavioral biometrics
        sessionStorage.setItem('ilfAnswers', JSON.stringify(newAnswers));
        sessionStorage.setItem('ilfLatencies', JSON.stringify(newLatencies));
        sessionStorage.setItem('ilfQuestions', JSON.stringify(newQuestions));
        sessionStorage.setItem('isLLMSession', 'true');
        
        navigate('/assess/processing');
      } else {
        console.error("Unknown status", result);
        setIsLoading(false);
        setError("Received an unrecognized response from the AI. Please try again.");
        setIsVisible(true);
      }
    } catch (err) {
      console.error("Failed to submit answer", err);
      setIsLoading(false);
      setError(err.message || "Connection failed");
      setIsVisible(true); // Fix the blank screen bug!
    }
  };

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    setError(null);

    if (retryCount >= 2) {
      // After 2 failed retries, offer demo fallback
      sessionStorage.removeItem('llmSession');
      sessionStorage.removeItem('nextQuestion');
      navigate('/assess');
      return;
    }

    // Re-render the current question
    setIsLoading(false);
    setIsVisible(true);
  };

  if (!questionData) return null;

  // Progress ring animation
  const ringProgress = Math.min(questionCount * 12.5, 95);
  const circumference = 2 * Math.PI * 40;
  const dashOffset = circumference - (ringProgress / 100) * circumference;

  return (
    <div style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* ── Adaptive Progress Ring ── */}
      <div style={{ position: 'fixed', top: '2rem', right: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
        <svg width="90" height="90" viewBox="0 0 90 90">
          <circle cx="45" cy="45" r="40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
          <circle 
            cx="45" cy="45" r="40" fill="none" 
            stroke="var(--neon-mint)" strokeWidth="3" 
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{ transition: 'stroke-dashoffset 0.8s ease', transform: 'rotate(-90deg)', transformOrigin: '45px 45px' }}
          />
          <text x="45" y="42" textAnchor="middle" fill="var(--text-primary)" fontFamily="Outfit" fontWeight="700" fontSize="20">{questionCount}</text>
          <text x="45" y="57" textAnchor="middle" fill="var(--text-muted)" fontFamily="Inter" fontSize="9" letterSpacing="1">LAYER</text>
        </svg>
      </div>

      {/* ── Main Content ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '2rem', opacity: isVisible ? 1 : 0, transition: 'opacity 0.3s ease' }}>
        
        {/* Mode indicator */}
        {isLLMSession && (
          <div style={{ 
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.2)',
            borderRadius: '50px', padding: '0.4rem 1rem', marginBottom: '1.5rem',
            fontSize: '0.75rem', color: 'var(--neon-mint)', letterSpacing: '2px', textTransform: 'uppercase'
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--neon-mint)', animation: 'pulse 2s infinite' }}></span>
            Adaptive AI Interview
          </div>
        )}
        
        {error ? (
          /* ── Error Recovery UI ── */
          <div className="slide-up" style={{ textAlign: 'center', maxWidth: '500px' }}>
            <div style={{ 
              background: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.3)',
              borderRadius: '16px', padding: '2rem', marginBottom: '2rem'
            }}>
              <h3 style={{ fontFamily: 'Outfit', color: 'var(--danger)', marginBottom: '1rem', fontSize: '1.3rem' }}>
                Connection Interrupted
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.5, marginBottom: '1.5rem' }}>
                {error}
              </p>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <button className="btn-outline" onClick={handleRetry} style={{ padding: '0.8rem 1.5rem' }}>
                  {retryCount >= 2 ? "Switch to Demo Mode" : `Retry (${2 - retryCount} left)`}
                </button>
              </div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="slide-up" style={{ textAlign: 'center' }}>
            <h2 className="pulse-text" style={{ fontFamily: 'Outfit', fontSize: '1.8rem', fontWeight: 600, marginBottom: '1rem' }}>
              {isLLMSession ? "Analyzing behavioral patterns..." : "Processing response..."}
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              {isLLMSession ? "The AI is calibrating the next layer of assessment" : "Computing biometric signals"}
            </p>
          </div>
        ) : (
          <>
            {/* Question dimension badge */}
            {questionData.dimension && (
              <span style={{ 
                color: 'var(--text-muted)', letterSpacing: '3px', textTransform: 'uppercase', 
                fontSize: '0.7rem', marginBottom: '1rem', fontWeight: 600,
                background: 'rgba(255,255,255,0.03)', padding: '0.3rem 0.8rem', borderRadius: '50px'
              }}>
                {questionData.dimension === 'stability' ? '◈ Stability' : 
                 questionData.dimension === 'planning' ? '◈ Planning' : 
                 questionData.dimension === 'resilience' ? '◈ Resilience' : '◈ Assessment'}
              </span>
            )}

            <h2 style={{ 
              fontFamily: 'Outfit', fontSize: '2.2rem', fontWeight: 600, 
              textAlign: 'center', maxWidth: '800px', lineHeight: 1.2, 
              marginBottom: '3rem', letterSpacing: '-1px'
            }}>
              {questionData.question_text}
            </h2>

            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: questionData.options?.length > 2 ? '1fr 1fr' : '1fr 1fr', 
              gap: '1rem', width: '100%', maxWidth: '650px' 
            }}>
              {questionData.options?.map((opt, i) => (
                <button 
                  key={i} 
                  className="btn-outline" 
                  onClick={() => handleAnswer(opt)} 
                  style={{ 
                    padding: '1.2rem 1.5rem', textAlign: 'left', fontSize: '0.95rem',
                    lineHeight: 1.4, transition: 'all 0.2s ease'
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── Conversation Recap (shows after 3+ questions in LLM mode) ── */}
      {isLLMSession && qaHistory.length >= 3 && !isLoading && !error && (
        <div style={{ 
          position: 'fixed', bottom: 0, left: 0, right: 0,
          background: 'linear-gradient(transparent, rgba(0,0,0,0.95) 30%)',
          padding: '3rem 2rem 1.5rem', 
          maxHeight: '180px', overflow: 'hidden'
        }}>
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <p style={{ 
              color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '2px', 
              textTransform: 'uppercase', marginBottom: '0.8rem' 
            }}>
              Interview Progress — {qaHistory.length} layers explored
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
              {qaHistory.slice(-3).map((qa, i) => (
                <div key={i} style={{ 
                  flex: '0 0 auto', minWidth: '200px', maxWidth: '260px',
                  background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)',
                  borderRadius: '10px', padding: '0.7rem 1rem', fontSize: '0.8rem'
                }}>
                  <div style={{ color: 'var(--text-muted)', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {qa.q?.substring(0, 50)}...
                  </div>
                  <div style={{ color: 'var(--neon-mint)', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    → {qa.a?.substring(0, 40)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
