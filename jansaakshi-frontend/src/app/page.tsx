'use client';

import { useState, useEffect, useCallback, FormEvent } from 'react';
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

interface StatsData {
  total_projects?: number;
  delayed_projects?: number;
  total_budget?: number;
  total_wards?: number;
}

export default function HomePage() {
  const { user, city, apiFetch } = useApp();
  const [stats, setStats] = useState<StatsData>({});
  const [delayed, setDelayed] = useState<any[]>([]);
  const [selectedWard, setSelectedWard] = useState<{ no: string; name: string } | null>(null);
  const [wardProjects, setWardProjects] = useState<any[]>([]);
  const [userWardProjects, setUserWardProjects] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);

  // Smart search state
  const [query, setQuery] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);
  const [searching, setSearching] = useState(false);

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

  useEffect(() => {
    if (!user?.ward || !connected) return;
    apiFetch(`/api/projects/ward/${user.ward}`)
      .then(r => r.json())
      .then(d => setUserWardProjects(d.projects || []))
      .catch(() => { });
  }, [user, connected, apiFetch]);

  const handleSearch = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchResult(null);
    try {
      const res = await apiFetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, city }),
      });
      if (res.ok) {
        setSearchResult(await res.json());
      } else {
        setSearchResult({ success: false, error: 'Search failed. Please try again.' });
      }
    } catch {
      setSearchResult({ success: false, error: 'Cannot connect to backend. Make sure the server is running.' });
    }
    setSearching(false);
  };

  const handleWardClick = async (wardNo: string, wardName: string) => {
    setSelectedWard({ no: wardNo, name: wardName });
    try {
      const res = await apiFetch(`/api/projects/ward/${wardNo}`);
      if (res.ok) setWardProjects((await res.json()).projects || []);
    } catch { }
  };

  const statusBadge = (s: string) => `status-badge status-${s || 'pending'}`;
  const cityLabel = city === 'delhi' ? 'Delhi' : 'Mumbai';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Smart Search Bar */}
      <div className="card" style={{ padding: '20px 24px', background: 'linear-gradient(135deg, var(--primary-light), var(--bg-card))', borderColor: '#bfdbfe' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px', color: 'var(--text)' }}>
          Ask about any project
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          Search by project name, ward, area, or ask a question in natural language
        </p>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px' }}>
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`e.g. "Charkop water pipeline" or "delayed projects in Kandivali"`}
            style={{ flex: 1, fontSize: '14px', padding: '10px 14px' }}
          />
          <button type="submit" className="btn btn-primary" disabled={searching} style={{ whiteSpace: 'nowrap', padding: '10px 20px' }}>
            {searching ? 'Searching...' : 'Search'}
          </button>
        </form>

        {/* Quick suggestion chips */}
        {!searchResult && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px' }}>
            {[
              city === 'mumbai' ? 'Kandivali road projects' : 'Chandni Chowk redesign',
              'Delayed projects',
              city === 'mumbai' ? 'Water pipeline update' : 'Rohini water ATMs',
              'Healthcare projects',
            ].map((s) => (
              <button key={s} onClick={() => { setQuery(s); }}
                style={{
                  padding: '4px 10px', borderRadius: '14px', border: '1px solid var(--border)',
                  background: 'var(--bg)', fontSize: '12px', color: 'var(--text-secondary)',
                  cursor: 'pointer', transition: 'all .15s',
                }}>
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Search Results */}
      {searchResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {searchResult.error ? (
            <div className="card" style={{ background: 'var(--red-bg)', borderColor: '#fecaca' }}>
              <p style={{ color: 'var(--red)', fontSize: '14px', fontWeight: 500 }}>{searchResult.error}</p>
            </div>
          ) : searchResult.found === false ? (
            /* Professional no-data message */
            <div className="card" style={{ borderLeft: '3px solid var(--amber)' }}>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                <div style={{ fontSize: '24px', lineHeight: 1 }}>📋</div>
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '6px', color: 'var(--text)' }}>No Data Available</h3>
                  <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '10px' }}>
                    {searchResult.answer}
                  </p>
                  {searchResult.suggestions?.length > 0 && (
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                      <strong>Try:</strong>
                      <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                        {searchResult.suggestions.map((s, i) => (
                          <li key={i} style={{ marginBottom: '2px' }}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
              <button className="btn btn-outline" style={{ marginTop: '10px', fontSize: '13px' }}
                onClick={() => setSearchResult(null)}>
                Clear search
              </button>
            </div>
          ) : (
            /* Found results */
            <>
              <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--primary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.3px' }}>
                    AI Summary
                  </span>
                  <button onClick={() => setSearchResult(null)} style={{
                    background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', color: 'var(--text-muted)',
                  }}>✕ Clear</button>
                </div>
                <p style={{ fontSize: '14px', lineHeight: 1.7, color: 'var(--text)' }}>{searchResult.answer}</p>
              </div>
              {searchResult.projects?.length > 0 && (
                <div className="card">
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
                    {searchResult.projects_count} project{searchResult.projects_count !== 1 ? 's' : ''} found
                  </p>
                  {searchResult.projects.map((p, i) => (
                    <div key={i} className="project-item">
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="project-name">{p.project_name}</div>
                        {p.summary && <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '3px' }}>{p.summary}</p>}
                        <div className="project-meta">
                          Ward {p.ward_no} – {p.ward_name}{p.ward_zone ? ` (${p.ward_zone})` : ''}
                          {p.budget ? ` · ₹${(p.budget / 100000).toFixed(1)}L` : ''}
                          {p.contractor_name ? ` · ${p.contractor_name}` : ''}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '12px' }}>
                        <span className={statusBadge(p.status)}>{p.status}</span>
                        {p.delay_days > 0 && <div style={{ fontSize: '12px', color: 'var(--red)', marginTop: '3px', fontWeight: 600 }}>{p.delay_days}d late</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* User Ward */}
      {user?.ward && userWardProjects.length > 0 && (
        <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
          <div className="card-header">
            <h2 className="card-title">Your Ward: {user.ward}</h2>
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
          <h2 className="card-title">Ward Map — {cityLabel}</h2>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Click a ward to see live stats</span>
        </div>
        <WardMap />
      </div>

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
              <div className="project-meta">Ward {p.ward_no} · {p.ward_name}{p.ward_zone ? ` (${p.ward_zone})` : ''}</div>
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
