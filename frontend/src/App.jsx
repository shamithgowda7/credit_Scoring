import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './components/Landing';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Welcome from './components/Welcome';
import ILFQuestions from './components/ILFQuestions';
import Processing from './components/Processing';
import Results from './components/Results';
import KnowledgeGraphPage from './components/KnowledgeGraph';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing — full-bleed marketing page (no sidebar) */}
        <Route path="/" element={<Landing />} />

        {/* Internal pages — wrapped in sidebar layout */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
          <Route path="/assess" element={<Welcome />} />
          <Route path="/assess/questions" element={<ILFQuestions />} />
          <Route path="/assess/processing" element={<Processing />} />
          <Route path="/assess/results" element={<Results />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
