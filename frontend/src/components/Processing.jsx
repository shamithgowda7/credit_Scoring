import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Processing() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const steps = [
    "Establishing secure connection...",
    "Capturing sub-millisecond behavioral biometrics...",
    "Executing Inverse Latency Function (ILF)...",
    "Running Causal AI engine...",
    "Evaluating stress resilience...",
    "Finalizing dynamic offer..."
  ];

  useEffect(() => {
    const processData = async () => {
      try {
        const userStr = sessionStorage.getItem('selectedUser');
        const ansStr = sessionStorage.getItem('ilfAnswers');
        const latStr = sessionStorage.getItem('ilfLatencies');

        if (!userStr || !ansStr || !latStr) {
          navigate('/assess');
          return;
        }

        const user = JSON.parse(userStr);
        const answers = JSON.parse(ansStr);
        const latencies = JSON.parse(latStr);

        setStep(1); // Behavioral
        const ilfRes = await fetch('http://127.0.0.1:8000/ilf-score', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ latencies, answers })
        });
        const ilfData = await ilfRes.json();
        sessionStorage.setItem('ilfResult', JSON.stringify(ilfData));

        setStep(3); // Causal AI
        await new Promise(r => setTimeout(r, 600));

        const scoreRes = await fetch('http://127.0.0.1:8000/score', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ features: user.features })
        });
        const scoreData = await scoreRes.json();
        sessionStorage.setItem('scoreResult', JSON.stringify(scoreData));

        setStep(5); // Finalizing
        await new Promise(r => setTimeout(r, 600));

        navigate('/assess/results');
      } catch (err) {
        console.error("Processing error", err);
        setStep("Error: Connection terminated. Is uvicorn running?");
      }
    };

    // Initial dramatic delay
    setTimeout(() => {
      processData();
    }, 800);
  }, [navigate]);

  return (
    <div style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
      <h2 className="pulse-text" style={{ fontFamily: 'Outfit', fontSize: '1.5rem', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', textAlign: 'center' }}>
        {typeof step === 'number' ? steps[step] : step}
      </h2>
      
      {/* Sleek minimal loader line */}
      <div style={{ marginTop: '3rem', width: '200px', height: '1px', background: 'var(--border-subtle)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ 
          position: 'absolute', top: 0, left: 0, height: '100%', width: '30%', 
          background: 'var(--neon-mint)',
          boxShadow: '0 0 10px var(--neon-mint-glow)',
          animation: 'shimmer 1.5s infinite ease-in-out'
        }}></div>
      </div>
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  );
}
