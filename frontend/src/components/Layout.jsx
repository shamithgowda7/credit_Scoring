import { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4' },
  { to: '/knowledge-graph', label: 'Knowledge Graph', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { to: '/assess', label: 'New Assessment', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [apiOk, setApiOk] = useState(false);
  const location = useLocation();

  useEffect(() => {
    fetch('http://127.0.0.1:8000/health').then(r => r.ok && setApiOk(true)).catch(() => {});
  }, []);

  const pageTitle = NAV.find(n => location.pathname.startsWith(n.to))?.label || 'Dashboard';

  return (
    <div className="app-layout">
      <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
        <div className="sidebar-brand">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="12" stroke="#00e68a" strokeWidth="2.5"/><path d="M10 14l3 3 5-6" stroke="#00e68a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          <span>CausalScore</span>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(n => (
            <NavLink key={n.to} to={n.to} className={({isActive}) => `nav-item${isActive ? ' active' : ''}`}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={n.icon}/></svg>
              <span className="nav-label">{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="sidebar-toggle" onClick={() => setCollapsed(c => !c)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d={collapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'}/></svg>
            <span>{collapsed ? '' : 'Collapse'}</span>
          </button>
        </div>
      </aside>
      <div className={`main-content${collapsed ? ' expanded' : ''}`}>
        <header className="topbar">
          <h1 className="topbar-title">{pageTitle}</h1>
          <div className="topbar-actions">
            <span style={{display:'flex',alignItems:'center',gap:6,fontSize:'0.82rem',color: apiOk ? '#00e68a' : '#f43f5e'}}>
              <span className="status-dot" style={{background: apiOk ? '#00e68a' : '#f43f5e'}}/>
              {apiOk ? 'API Connected' : 'API Offline'}
            </span>
            <NavLink to="/assess" className="btn btn-primary btn-sm">+ New Assessment</NavLink>
          </div>
        </header>
        <div className="page-body">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
