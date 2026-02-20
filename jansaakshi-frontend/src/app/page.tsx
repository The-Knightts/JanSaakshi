'use client';

import { useState, useEffect, useCallback, FormEvent } from 'react';
import { useApp } from '@/context/AppContext';
import dynamic from 'next/dynamic';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ArrowRight } from 'lucide-react';

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


  const statusBadge = (s: string) => `status-badge status-${s || 'pending'}`;
  const cityLabel = city === 'delhi' ? 'Delhi' : 'Mumbai';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="flex flex-col gap-8 w-full max-w-[1400px] mx-auto pb-20">
        {/* Hero Section with Mumbai Touch */}
        <section className="relative px-8 pt-10 pb-20 md:pt-14 md:pb-32 rounded-[3rem] overflow-hidden bg-[#0A1128] text-white shadow-2xl">
          {/* Animated Sea Waves Pattern */}
          <div className="absolute inset-0 opacity-10 sea-pattern animate-[pulse_8s_infinite]" />

          {/* Mumbai Sunset Glow */}
          <div className="absolute top-[-10%] right-[-10%] w-[600px] h-[600px] bg-orange-600/20 rounded-full blur-[150px] animate-pulse" />
          <div className="absolute bottom-[-20%] left-[-10%] w-[400px] h-[400px] bg-blue-600/20 rounded-full blur-[120px]" />

          <div className="relative z-10 max-w-4xl">
            <div className="flex items-center gap-3 mb-8">
              <Badge className="bg-primary/20 text-blue-300 border-none px-4 py-1.5 backdrop-blur-xl font-bold uppercase tracking-widest text-[10px]">
                Maximum City Dashboard
              </Badge>
              <div className="h-1 w-12 bg-gradient-to-r from-primary to-transparent rounded-full" />
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">आमची मुंबई • Our City</span>
            </div>

            <h1 className="text-5xl md:text-8xl font-black tracking-[ -0.05em] mb-8 leading-[0.95]">
              Legacy of <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-amber-200">
                Maximum Progress.
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-slate-300 max-w-2xl mb-12 leading-relaxed font-light">
              Bringing transparency to the <span className="text-white font-semibold">Gateway of India&apos;s</span> future. Track infra, report issues, and build the dream.
            </p>

            <div className="flex flex-wrap gap-5 items-center">
              <Button size="lg" className="bg-primary hover:bg-white hover:text-primary h-16 px-10 rounded-2xl font-black text-lg transition-all shadow-2xl shadow-primary/40 group">
                Explore Live Map
                <ArrowRight className="ml-2 group-hover:translate-x-2 transition-transform" />
              </Button>
              <Button size="lg" variant="outline" className="border-white/10 hover:bg-white/5 h-16 px-10 rounded-2xl font-black text-lg backdrop-blur-md">
                Public Grievances
              </Button>
            </div>
          </div>
        </section>

        <div className="flex flex-col gap-8">
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
      </div>
    </div>
  );
}
