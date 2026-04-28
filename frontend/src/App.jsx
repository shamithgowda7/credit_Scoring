import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './components/Landing';
import Dashboard from './components/Dashboard';
import Welcome from './components/Welcome';
import ILFQuestions from './components/ILFQuestions';
import Processing from './components/Processing';
import Results from './components/Results';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Section 1: B2B Marketing / Onboarding */}
        <Route path="/" element={<Landing />} />

        {/* Section 2: Bank-Facing Dashboard */}
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Section 3: User-Facing Assessment */}
        <Route path="/assess" element={<Welcome />} />
        <Route path="/assess/questions" element={<ILFQuestions />} />
        <Route path="/assess/processing" element={<Processing />} />
        <Route path="/assess/results" element={<Results />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
