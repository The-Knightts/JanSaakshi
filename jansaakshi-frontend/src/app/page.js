'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApp } from '@/context/AppContext';
import dynamic from 'next/dynamic';

const WardMap = dynamic(() => import('@/components/WardMap'), {
  ssr: false,
  loading: () => (
    <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc', borderRadius: '10px', border: '1px solid var(--border)' }}>
      <p style={{ color: 'var(--text-muted)' }}>Loading map...</p>
    </div>
  ),
});

export default function HomePage() {
  const { user, city, apiFetch } = useApp();
  const [stats, setStats] = useState({});
  const [delayed, setDelayed] = useState([]);
  const [selectedWard, setSelectedWard] = useState(null);
  const [wardProjects, setWardProjects] = useState([]);
  const [userWardProjects, setUserWardProjects] = useState([]);
  const [connected, setConnected] = useState(false);

  const load = useCallback(async () => {
    try {
      const [sRes, dRes] = await Promise.all([
        apiFetch('/api/stats'), apiFetch('/api/projects/delayed'),
      ]);
      if (sRes.ok) { setStats(await sRes.json()); setConnected(true); }
      if (dRes.ok) { const d = await dRes.json(); setDelayed(Array.isArray(d) ? d.slice(0, 5) : []); }
    } catch { setConnected(false); }
  }, [apiFetch]);

  useEffect(() => { load(); }, [load]);

  // Load user's ward projects
  useEffect(() => {
    if (!user?.ward_number || !connected) return;
    apiFetch(`/api/projects/ward/${user.ward_number}`)
      .then(r => r.json())
      .then(d => setUserWardProjects(d.projects || []))
      .catch(() => { });
  }, [user, connected, apiFetch]);

  const handleWardClick = async (wardNumber, wardName) => {
    setSelectedWard({ number: wardNumber, name: wardName });
    try {
      const res = await apiFetch(`/api/projects/ward/${wardNumber}`);
      if (res.ok) setWardProjects((await res.json()).projects || []);
    } catch { }
  };

  const statusBadge = (s) => `status-badge status-${s || 'pending'}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* User's ward (logged in) */}
      {user?.ward_number && userWardProjects.length > 0 && (
        <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
          <div className="card-header">
            <h2 className="card-title">Your Ward: {user.ward_number}</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{userWardProjects.length} projects</span>
          </div>
          {userWardProjects.slice(0, 3).map((p, i) => (
            <div key={i} className="project-item">
              <div>
                <div className="project-name">{p.project_name}</div>
                <div className="project-meta">{p.location_details}</div>
              </div>
              <span className={statusBadge(p.status)}>{p.status}</span>
            </div>
          ))}
          {userWardProjects.length > 3 && (
            <a href="/projects" style={{ fontSize: '13px', color: 'var(--primary)', textDecoration: 'none', marginTop: '8px', display: 'block' }}>
              View all {userWardProjects.length} projects →
            </a>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--primary)' }}>{stats.total_projects || 0}</div>
          <div className="stat-label">Total Projects</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--red)' }}>{stats.delayed_projects || 0}</div>
          <div className="stat-label">Delayed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_budget ? `₹${(stats.total_budget / 10000000).toFixed(0)}Cr` : '₹0'}</div>
          <div className="stat-label">Total Budget</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--amber)' }}>{stats.total_wards || 0}</div>
          <div className="stat-label">Wards</div>
        </div>
      </div>

      {!connected && (
        <div className="card" style={{ background: 'var(--amber-bg)', borderColor: '#fde68a' }}>
          <p style={{ color: 'var(--amber)', fontSize: '13px', fontWeight: 500 }}>
            Backend not connected. Run <code style={{ background: '#fff', padding: '2px 6px', borderRadius: '4px', fontSize: '12px' }}>python app.py</code>
          </p>
        </div>
      )}

      {/* Map */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="card-title">Ward Map — {city === 'delhi' ? 'Delhi' : 'Mumbai'}</h2>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Click a ward to see projects</span>
        </div>
        <WardMap city={city} onWardClick={handleWardClick} />
      </div>

      {/* Ward Detail Panel */}
      {selectedWard && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Ward {selectedWard.number} — {selectedWard.name}</h2>
            <button
              className="btn btn-outline"
              style={{ fontSize: '12px', padding: '4px 10px' }}
              onClick={() => setSelectedWard(null)}
            >
              Close
            </button>
          </div>
          {wardProjects.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No projects in this ward.</p>
          ) : (
            wardProjects.map((p, i) => (
              <div key={i} className="project-item">
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="project-name">{p.project_name}</div>
                  {p.summary && <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '3px' }}>{p.summary}</p>}
                  <div className="project-meta">
                    {p.budget_amount ? `₹${(p.budget_amount / 100000).toFixed(1)}L` : ''}
                    {p.contractor_name ? ` · ${p.contractor_name}` : ''}
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '12px' }}>
                  <span className={statusBadge(p.status)}>{p.status}</span>
                  {p.delay_days > 0 && <div style={{ fontSize: '12px', color: 'var(--red)', marginTop: '3px', fontWeight: 600 }}>{p.delay_days}d late</div>}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Delayed */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Most Delayed Projects</h2>
          <a href="/projects?status=delayed" className="btn btn-outline" style={{ fontSize: '12px', padding: '5px 10px' }}>View All</a>
        </div>
        {delayed.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>{connected ? 'No delayed projects.' : 'Connect to API.'}</p>
        ) : delayed.map((p, i) => (
          <div key={i} className="project-item">
            <div>
              <div className="project-name">{p.project_name}</div>
              <div className="project-meta">Ward {p.ward_number} · {p.ward_name}</div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <span className={statusBadge(p.status)}>{p.status}</span>
              {p.delay_days > 0 && <div style={{ fontSize: '12px', color: 'var(--red)', marginTop: '3px', fontWeight: 600 }}>{p.delay_days}d overdue</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
