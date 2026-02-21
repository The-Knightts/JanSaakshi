'use client';

import { useState, useEffect, useCallback, FormEvent } from 'react';
import { PiClipboardLight, PiProhibitLight } from 'react-icons/pi';
import { useApp } from '@/context/AppContext';
import dynamic from 'next/dynamic';
import { Building2, AlertCircle, TrendingUp, ArrowRight, ArrowLeft } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

// Mock Card components if they don't exist elsewhere
const Card = ({ children, className, style }: any) => <div className={className} style={style}>{children}</div>;
const CardHeader = ({ children, className }: any) => <div className={className}>{children}</div>;
const CardTitle = ({ children, className }: any) => <h3 className={className}>{children}</h3>;
const CardContent = ({ children, className }: any) => <div className={className}>{children}</div>;


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

  const [query, setQuery] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);
  const [searching, setSearching] = useState(false);
  const [selectedWard, setSelectedWard] = useState<any>(null);
  const [wardProjects, setWardProjects] = useState<any[]>([]);


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

  useEffect(() => {
    const handleWardClick = async (e: any) => {
      const wardNumber = e.detail;
      setSelectedWard({ number: wardNumber, name: `Ward ${wardNumber}` });
      try {
        const res = await apiFetch(`/api/projects/ward/${wardNumber}`);
        if (res.ok) {
          const data = await res.json();
          setWardProjects(data.projects || []);
        }
      } catch (err) {
        console.error(err);
      }
    };
    window.addEventListener('ward-click', handleWardClick);
    return () => window.removeEventListener('ward-click', handleWardClick);
  }, [apiFetch]);

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
    <div className="space-y-6 w-full">

      {/* ── Hero ── */}
      <div style={{
        position: 'relative', overflow: 'hidden', borderRadius: '16px',
        background: 'linear-gradient(135deg, #0a1628 0%, #0d1f3c 50%, #0a1628 100%)',
        padding: '48px 48px 52px', minHeight: '280px',
        border: '1px solid rgba(255,255,255,0.06)',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/HACKSPARK_mUMBAI.png" alt="" aria-hidden="true" style={{
          position: 'absolute', right: 0, bottom: 0,
          height: '100%', width: '60%',
          objectFit: 'contain', objectPosition: 'right bottom',
          opacity: 0.18, pointerEvents: 'none', mixBlendMode: 'luminosity',
        }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: '55%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <span style={{
              background: 'rgba(29,78,216,0.8)', color: '#93c5fd',
              fontSize: '10px', fontWeight: 700, letterSpacing: '0.12em',
              padding: '4px 10px', borderRadius: '20px', textTransform: 'uppercase',
            }}>Maximum City Dashboard</span>
            <span style={{ width: '40px', height: '1px', background: 'rgba(255,255,255,0.2)' }} />
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.45)', letterSpacing: '0.05em' }}>
              आमची मुंबई · OUR CITY
            </span>
          </div>

          <h1 style={{ fontSize: '52px', fontWeight: 800, lineHeight: 1.1, marginBottom: '16px' }}>
            <span style={{ color: '#ffffff', display: 'block' }}>Legacy of</span>
            <span style={{ display: 'block' }}>
              <span style={{ color: '#60a5fa' }}>Maximum </span>
              <span style={{ color: '#fbbf24' }}>Progress.</span>
            </span>
          </h1>

          <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.55)', lineHeight: 1.7, marginBottom: '28px', maxWidth: '380px' }}>
            Bringing transparency to the{' '}
            <strong style={{ color: 'rgba(255,255,255,0.8)', fontWeight: 600 }}>
              {cityLabel === 'Delhi' ? "Capital of India's" : "Gateway of India's"}
            </strong>
            {' '}future. Track infra, report issues, and build the dream.
          </p>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <a href="/map" style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              background: '#1d4ed8', color: '#ffffff',
              padding: '12px 24px', borderRadius: '10px',
              fontWeight: 600, fontSize: '14px', textDecoration: 'none',
            }}>Explore Live Map →</a>
            <a href="/complaints" style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              background: 'rgba(255,255,255,0.07)', color: '#ffffff',
              padding: '12px 24px', borderRadius: '10px',
              fontWeight: 600, fontSize: '14px', textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.15)',
            }}>Public Grievances</a>
          </div>
        </div>
      </div>

      {/* ── Search Card ── */}
      <div className="card" style={{ padding: '20px 24px', background: 'linear-gradient(135deg, var(--primary-light), var(--bg-card))', borderColor: '#bfdbfe', margin: '40px 20px 40px 20px' }}>
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

        {!searchResult && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px' }}>
            {[
              city === 'mumbai' ? 'Kandivali road projects' : 'Chandni Chowk redesign',
              'Delayed projects',
              city === 'mumbai' ? 'Water pipeline update' : 'Rohini water ATMs',
              'Healthcare projects',
            ].map((s) => (
              <button key={s} onClick={() => setQuery(s)} style={{
                padding: '4px 10px', borderRadius: '14px', border: '1px solid var(--border)',
                background: 'var(--bg)', fontSize: '12px', color: 'var(--text-secondary)',
                cursor: 'pointer', transition: 'all .15s',
              }}>{s}</button>
            ))}
          </div>
        )}
      </div>

      {/* ── Search Results ── */}
      {searchResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {searchResult.error ? (
            <div className="card" style={{ background: 'var(--red-bg)', borderColor: '#fecaca' }}>
              <p style={{ color: 'var(--red)', fontSize: '14px', fontWeight: 500 }}>{searchResult.error}</p>
            </div>
          ) : searchResult.found === false ? (
            <div className="card" style={{ borderLeft: '3px solid var(--amber)' }}>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                <div style={{ fontSize: '24px', lineHeight: 1, color: 'var(--amber)' }}>
                  <PiClipboardLight size={24} />
                </div>
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '6px', color: 'var(--text)' }}>No Data Available</h3>
                  <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '10px' }}>
                    {searchResult.answer}
                  </p>
                  {searchResult.suggestions?.length > 0 && (
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                      <strong>Try:</strong>
                      <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                        {searchResult.suggestions.map((s: string, i: number) => (
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
            <>
              <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--primary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.3px' }}>
                    AI Summary
                  </span>
                  <button onClick={() => setSearchResult(null)} style={{
                    background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px',
                    color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px',
                  }}>
                    <PiProhibitLight size={14} /> Clear
                  </button>
                </div>
                <p style={{ fontSize: '14px', lineHeight: 1.7, color: 'var(--text)' }}>{searchResult.answer}</p>
              </div>
              {searchResult.projects?.length > 0 && (
                <div className="card">
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
                    {searchResult.projects_count} project{searchResult.projects_count !== 1 ? 's' : ''} found
                  </p>
                  {searchResult.projects.map((p: any, i: number) => (
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
                        {p.delay_days > 0 && (
                          <div style={{ fontSize: '12px', color: 'var(--red)', marginTop: '3px', fontWeight: 600 }}>
                            {p.delay_days}d late
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── User Ward ── */}
      {user?.ward && userWardProjects.length > 0 && (
        <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
          <div className="card-header">
            <h2 className="card-title">Your Ward: {user.ward}</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{userWardProjects.length} projects</span>
          </div>
          {userWardProjects.slice(0, 3).map((p: any, i: number) => (
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

      <div className="stats-premium">

        <div className="weather-premium">
          <div className="weather-title">
            Mumbai Live Weather
          </div>
          <div className="weather-temp">
            28°C
          </div>
          <div className="weather-meta">
            Partly Cloudy • AQI: 84
          </div>
        </div>

        <div className="stat-premium">
          <div className="stat-premium-value">
            {stats.total_projects || 0}
          </div>
          <div className="stat-premium-label">
            Total Projects
          </div>
        </div>

        <div className="stat-premium">
          <div className="stat-premium-value">
            {stats.delayed_projects || 0}
          </div>
          <div className="stat-premium-label">
            Delayed Projects
          </div>
        </div>

        <div className="stat-premium">
          <div className="stat-premium-value">
            ₹{((stats.total_budget || 0) / 10000000).toFixed(0)}Cr
          </div>
          <div className="stat-premium-label">
            Total Budget
          </div>
        </div>

      </div>
      {/* ───── Main Dashboard Grid ───── */}
      <div className="dashboard-grid">
        {/* LEFT SIDE */}
        <div className="dashboard-left">
          <div className="map-card">

            <div className="map-header">
              <div>
                <div className="map-title">
                  Infrastructure Map
                </div>
                <div className="map-subtitle">
                  Greater Mumbai Region
                </div>
              </div>

              <span className="status-badge status-approved">
                Interactive Layers
              </span>
            </div>

            <div className="map-container-inner">
              <WardMap />
            </div>
          </div>

        </div>
        {/* Right: Side Info Panel */}
        <div className="dashboard-right">
          {/* Ward Detail Panel (Conditional) */}
          <div className="alert-card">

            <div className="alert-header">
              <div className="alert-title">
                Alert Center
              </div>
              <AlertCircle color="#f59e0b" size={22} />
            </div>

            <div className="alert-list">
              {delayed.map((p, i) => (
                <div key={i} className="alert-item">

                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div className="alert-name">
                      {p.project_name}
                    </div>

                    <span className="alert-delay">
                      {p.delay_days}d late
                    </span>
                  </div>

                  <div className="alert-ward">
                    {p.ward_name}
                  </div>

                </div>
              ))}
            </div>

            <div className="alert-footer">
              <div className="alert-footer-title">
                Live Feed
              </div>

              <div>
                <span className="alert-live-dot"></span>
                Tracking 1,248 active development sites across the city.
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
