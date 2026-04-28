import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const QUESTIONS = [
  { id: 1, text: "I feel confident about handling unexpected expenses." },
  { id: 2, text: "I usually know exactly how much money I'll have next week." },
  { id: 3, text: "I can hold my breath underwater for 10 minutes." },
];

export default function ILFQuestions() {
  const navigate = useNavigate();
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [latencies, setLatencies] = useState([]);
  const [isVisible, setIsVisible] = useState(true);
  
  const renderTimeRef = useRef(0);

  useEffect(() => {
    renderTimeRef.current = performance.now();
    setIsVisible(true);
  }, [currentQ]);

  const handleAnswer = (answer) => {
    const clickTime = performance.now();
    const latencySec = (clickTime - renderTimeRef.current) / 1000;

    const newAnswers = [...answers, answer];
    const newLatencies = [...latencies, latencySec];

    setIsVisible(false); // trigger fade out

    setTimeout(() => {
      if (currentQ < QUESTIONS.length - 1) {
        setAnswers(newAnswers);
        setLatencies(newLatencies);
        setCurrentQ(prev => prev + 1);
      } else {
        sessionStorage.setItem('ilfAnswers', JSON.stringify(newAnswers));
        sessionStorage.setItem('ilfLatencies', JSON.stringify(newLatencies));
        navigate('/assess/processing');
      }
    }, 300); // Wait for fade out animation
  };

  const q = QUESTIONS[currentQ];
  const progress = ((currentQ + 1) / QUESTIONS.length) * 100;

  return (
    <div style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* 1px Minimal Progress Bar */}
      <div className="progress-container" style={{ position: 'fixed', top: 0, left: 0 }}>
        <div className="progress-bar" style={{ width: `${progress}%` }}></div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity: isVisible ? 1 : 0, transition: 'opacity 0.3s ease' }}>
        
        <p style={{ color: 'var(--text-muted)', letterSpacing: '3px', textTransform: 'uppercase', fontSize: '0.8rem', marginBottom: '2rem' }}>
          0{currentQ + 1} / 0{QUESTIONS.length}
        </p>
        
        <h2 style={{ fontFamily: 'Outfit', fontSize: '3rem', fontWeight: 600, textAlign: 'center', maxWidth: '800px', lineHeight: 1.2, marginBottom: '4rem', letterSpacing: '-1px' }}>
          {q.text}
        </h2>

        <div style={{ display: 'flex', gap: '1.5rem', width: '100%', maxWidth: '400px' }}>
          <button className="btn-outline" onClick={() => handleAnswer('Agree')} style={{ flex: 1, padding: '1.2rem' }}>
            Agree
          </button>
          <button className="btn-outline" onClick={() => handleAnswer('Disagree')} style={{ flex: 1, padding: '1.2rem' }}>
            Disagree
          </button>
        </div>

      </div>
    </div>
  );
}
