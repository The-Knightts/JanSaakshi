'use client';

import { useState, useEffect, useCallback, Suspense, useRef } from 'react';
import { useApp } from '@/context/AppContext';
import { useSearchParams, useRouter } from 'next/navigation';

/* ─── Status config ─── */
const STATUS_CFG: Record<string, { bg: string; text: string; dot: string; glow: string }> = {
    completed: { bg: '#f0fdf4', text: '#16a34a', dot: '#16a34a', glow: 'rgba(22,163,74,0.15)' },
    ongoing: { bg: '#eff6ff', text: '#1d4ed8', dot: '#3b82f6', glow: 'rgba(59,130,246,0.15)' },
    delayed: { bg: '#fef2f2', text: '#dc2626', dot: '#ef4444', glow: 'rgba(239,68,68,0.15)' },
    stalled: { bg: '#fffbeb', text: '#d97706', dot: '#f59e0b', glow: 'rgba(245,158,11,0.15)' },
    approved: { bg: '#f5f3ff', text: '#7c3aed', dot: '#8b5cf6', glow: 'rgba(139,92,246,0.15)' },
    pending: { bg: '#f8fafc', text: '#64748b', dot: '#94a3b8', glow: 'rgba(148,163,184,0.1)' },
};
const cfg = (s: string) => STATUS_CFG[s?.toLowerCase()] ?? STATUS_CFG.pending;

const TYPE_ICONS: Record<string, string> = {
    roads: '🛣️', water_supply: '💧', drainage: '🌊', parks: '🌳',
    schools: '🏫', healthcare: '🏥', street_lighting: '💡', waste_management: '♻️',
};

const STATUS_TABS = ['all', 'ongoing', 'delayed', 'completed', 'stalled', 'approved'];

/* ─── Shimmer skeleton ─── */
function Skeleton() {
    return (
        <>
            <style>{`
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
        .proj-row { animation: fadeSlideIn 0.35s ease both; }
        .proj-row:hover .row-expand-hint { opacity: 1 !important; }
      `}</style>
            {[1, 2, 3, 4, 5].map(i => (
                <div key={i} style={{
                    height: '80px', borderRadius: '12px',
                    background: 'linear-gradient(90deg,#f1f5f9 25%,#e8edf5 50%,#f1f5f9 75%)',
                    backgroundSize: '200% 100%',
                    animation: `shimmer 1.4s ${i * 0.1}s infinite`,
                }} />
            ))}
        </>
    );
}

/* ─── Expandable Project Row ─── */
function ProjectRow({ p, index }: { p: any; index: number }) {
    const [open, setOpen] = useState(false);
    const s = cfg(p.status);

    return (
        <div
            className="proj-row"
            style={{ animationDelay: `${index * 0.05}s` }}
        >
            <div
                onClick={() => setOpen(o => !o)}
                style={{
                    display: 'flex', alignItems: 'flex-start', gap: '14px',
                    padding: '16px 16px',
                    borderRadius: open ? '12px 12px 0 0' : '12px',
                    border: `1px solid ${open ? s.dot : 'var(--border)'}`,
                    borderBottom: open ? 'none' : undefined,
                    background: open ? s.bg : '#fff',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                }}
                onMouseEnter={e => {
                    if (!open) {
                        (e.currentTarget as HTMLDivElement).style.boxShadow = `0 4px 20px ${s.glow}`;
                        (e.currentTarget as HTMLDivElement).style.borderColor = s.dot;
                        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)';
                    }
                }}
                onMouseLeave={e => {
                    if (!open) {
                        (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
                        (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)';
                        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
                    }
                }}
            >
                {/* Animated status dot */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', flexShrink: 0, paddingTop: '2px' }}>
                    <div style={{
                        width: '10px', height: '10px', borderRadius: '50%',
                        background: s.dot,
                        boxShadow: `0 0 0 3px ${s.glow}`,
                    }} />
                </div>

                {/* Main info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        {p.project_type && <span style={{ fontSize: '14px' }}>{TYPE_ICONS[p.project_type] || '📦'}</span>}
                        <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {p.project_name}
                        </span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', background: '#eff6ff', color: '#1d4ed8', fontWeight: 500 }}>
                            Ward {p.ward_no}{p.ward_name ? ` · ${p.ward_name}` : ''}
                        </span>
                        {p.budget > 0 && (
                            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', background: '#f0fdf4', color: '#16a34a', fontWeight: 500 }}>
                                ₹{(p.budget / 100000).toFixed(1)}L
                            </span>
                        )}
                        {p.contractor_name && (
                            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', background: '#f8fafc', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                                {p.contractor_name}
                            </span>
                        )}
                    </div>
                </div>

                {/* Right: Status + delay + chevron */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', flexShrink: 0 }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 10px', borderRadius: '12px', background: s.bg, color: s.text }}>
                        {p.status || 'pending'}
                    </span>
                    {p.delay_days > 0 && (
                        <span style={{ fontSize: '11px', color: 'var(--red)', fontWeight: 600 }}>⚠ {p.delay_days}d late</span>
                    )}
                    <span style={{
                        fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px',
                        transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s ease',
                        display: 'inline-block',
                    }}>▼</span>
                </div>
            </div>

            {/* Expanded detail panel */}
            <div style={{
                maxHeight: open ? '300px' : '0',
                overflow: 'hidden',
                transition: 'max-height 0.3s ease',
                border: open ? `1px solid ${s.dot}` : 'none',
                borderTop: 'none',
                borderRadius: '0 0 12px 12px',
                background: `linear-gradient(to bottom, ${s.bg}, #fff)`,
            }}>
                <div style={{ padding: '16px 20px 18px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '14px' }}>
                    {[
                        { label: 'Ward', value: `${p.ward_no}${p.ward_name ? ' – ' + p.ward_name : ''}` },
                        { label: 'Zone', value: p.ward_zone || '—' },
                        { label: 'Type', value: p.project_type ? (TYPE_ICONS[p.project_type] || '') + ' ' + p.project_type.replace(/_/g, ' ') : '—' },
                        { label: 'Budget', value: p.budget > 0 ? `₹${(p.budget / 100000).toFixed(2)}L` : '—' },
                        { label: 'Contractor', value: p.contractor_name || '—' },
                        { label: 'Delay', value: p.delay_days > 0 ? `${p.delay_days} days` : 'On schedule' },
                    ].map(({ label, value }) => (
                        <div key={label}>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '3px' }}>{label}</div>
                            <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text)' }}>{value}</div>
                        </div>
                    ))}
                    {p.summary && (
                        <div style={{ gridColumn: '1 / -1' }}>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '3px' }}>Summary</div>
                            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{p.summary}</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ─── Main component ─── */
function ProjectsList() {
    const { apiFetch } = useApp();
    const searchParams = useSearchParams();
    const router = useRouter();

    const [projects, setProjects] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeStatus, setActiveStatus] = useState(searchParams.get('status') || 'all');
    const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '');
    const [wardFilter, setWardFilter] = useState(searchParams.get('ward') || '');
    const [q, setQ] = useState(searchParams.get('q') || '');
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const load = useCallback(async (overrideQ?: string) => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            const status = activeStatus === 'all' ? '' : activeStatus;
            if (status) params.set('status', status);
            if (typeFilter) params.set('type', typeFilter);
            if (wardFilter) params.set('ward', wardFilter);
            if (overrideQ !== undefined ? overrideQ : q)
                params.set('q', overrideQ !== undefined ? overrideQ : q);
            const res = await apiFetch(`/api/projects?${params}`);
            if (res.ok) setProjects((await res.json()).projects || []);
        } catch { setProjects([]); }
        setLoading(false);
    }, [activeStatus, typeFilter, wardFilter, q, apiFetch]);

    useEffect(() => { load(); }, [activeStatus, typeFilter, wardFilter]);// eslint-disable-line

    /* Live search with debounce */
    const handleQChange = (val: string) => {
        setQ(val);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => load(val), 420);
    };

    const clearWard = () => {
        setWardFilter('');
        const params = new URLSearchParams(window.location.search);
        params.delete('ward');
        router.push(`/projects?${params.toString()}`);
    };

    /* Mini stats */
    const total = projects.length;
    const delayed = projects.filter(p => p.status?.toLowerCase() === 'delayed').length;
    const completed = projects.filter(p => p.status?.toLowerCase() === 'completed').length;
    const totalBudget = projects.reduce((s, p) => s + (Number(p.budget) || 0), 0);
    const budgetLabel = totalBudget >= 10000000
        ? `₹${(totalBudget / 10000000).toFixed(1)}Cr`
        : totalBudget >= 100000
            ? `₹${(totalBudget / 100000).toFixed(1)}L`
            : `₹${totalBudget > 0 ? totalBudget.toLocaleString('en-IN') : '0'}`;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1100px', margin: '0 auto', width: '100%' }}>
            <style>{`
        @keyframes fadeSlideIn { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        .proj-row { animation: fadeSlideIn 0.35s ease both; }
        .status-tab {
          padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
          cursor: pointer; border: 1.5px solid transparent;
          transition: all 0.18s ease; white-space: nowrap; background: none;
          color: var(--text-secondary);
        }
        .status-tab:hover { background: var(--bg); border-color: var(--border); }
        .status-tab.active { border-color: var(--primary); color: var(--primary); background: #eff6ff; }
        .stat-mini { animation: fadeSlideIn 0.4s ease both; }
      `}</style>

            {/* Page header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                    <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
                        Municipal Dashboard
                    </p>
                    <h1 style={{ fontSize: '30px', fontWeight: 800, color: 'var(--text)', lineHeight: 1.15, margin: 0 }}>
                        Projects
                    </h1>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Live infrastructure tracker — click any row to expand details
                    </p>
                </div>
                {wardFilter && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: '8px',
                        background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1d4ed8',
                        padding: '6px 14px', borderRadius: '20px', fontSize: '13px', fontWeight: 600,
                    }}>
                        📍 Ward {wardFilter}
                        <button onClick={clearWard} style={{ border: 'none', background: 'none', color: '#1d4ed8', cursor: 'pointer', fontSize: '18px', lineHeight: 1 }}>×</button>
                    </div>
                )}
            </div>

            {/* Mini stat cards */}
            {!loading && total > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                    {[
                        { label: 'Total', value: total, color: 'var(--primary)', bg: '#eff6ff', delay: '0s' },
                        { label: 'Delayed', value: delayed, color: 'var(--red)', bg: '#fef2f2', delay: '0.05s' },
                        { label: 'Completed', value: completed, color: '#16a34a', bg: '#f0fdf4', delay: '0.1s' },
                        { label: 'Budget', value: budgetLabel, color: '#d97706', bg: '#fffbeb', delay: '0.15s' },
                    ].map(({ label, value, color, bg, delay }) => (
                        <div key={label} className="stat-mini" style={{ animationDelay: delay, background: bg, borderRadius: '12px', padding: '14px 16px', border: `1px solid ${color}22` }}>
                            <div style={{ fontSize: '22px', fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 500 }}>{label}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Filter bar */}
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: '12px', padding: '14px 16px', boxShadow: 'var(--shadow)' }}>
                {/* Search row */}
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '12px', alignItems: 'center' }}>
                    <div style={{ position: 'relative', flex: '1 1 220px', minWidth: '180px' }}>
                        <svg style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}
                            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                        </svg>
                        <input className="input" placeholder="Live search projects…" value={q}
                            onChange={e => handleQChange(e.target.value)}
                            style={{ paddingLeft: '32px', width: '100%' }} />
                    </div>
                    <select className="input" value={typeFilter}
                        onChange={e => setTypeFilter(e.target.value)}
                        style={{ flex: '0 1 175px', minWidth: '130px' }}>
                        <option value="">All Types</option>
                        {Object.entries(TYPE_ICONS).map(([val, icon]) => (
                            <option key={val} value={val}>{icon} {val.replace(/_/g, ' ')}</option>
                        ))}
                    </select>
                    {(q || typeFilter || wardFilter) && (
                        <button onClick={() => { setQ(''); setTypeFilter(''); setWardFilter(''); setActiveStatus('all'); }}
                            style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '12px', borderRadius: '8px', padding: '8px 12px', cursor: 'pointer' }}>
                            ✕ Clear
                        </button>
                    )}
                </div>

                {/* Status tabs */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', overflow: 'hidden' }}>
                    {STATUS_TABS.map(tab => (
                        <button key={tab} className={`status-tab${activeStatus === tab ? ' active' : ''}`}
                            onClick={() => setActiveStatus(tab)}>
                            {tab === 'all' ? 'All' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                            {tab !== 'all' && !loading && (
                                <span style={{ marginLeft: '5px', opacity: 0.6 }}>
                                    ({projects.filter(p => p.status?.toLowerCase() === tab).length})
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Project rows */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {loading ? (
                    <Skeleton />
                ) : projects.length === 0 ? (
                    <div style={{
                        background: '#fff', border: '1px solid var(--border)', borderRadius: '12px',
                        textAlign: 'center', padding: '64px 20px', animation: 'fadeSlideIn 0.3s ease',
                    }}>
                        <div style={{ fontSize: '42px', marginBottom: '12px' }}>📋</div>
                        <p style={{ fontWeight: 700, color: 'var(--text)', fontSize: '16px', marginBottom: '4px' }}>No projects found</p>
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Try changing your filters or search term</p>
                    </div>
                ) : (
                    projects.map((p, i) => <ProjectRow key={i} p={p} index={i} />)
                )}
            </div>

            {/* Footer count */}
            {!loading && projects.length > 0 && (
                <p style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)', paddingBottom: '16px' }}>
                    Showing {projects.length} project{projects.length !== 1 ? 's' : ''}
                </p>
            )}
        </div>
    );
}

export default function ProjectsPage() {
    return (
        <Suspense fallback={
            <div style={{ padding: '40px 20px', maxWidth: '1100px', margin: '0 auto' }}>
                <div style={{ height: '36px', width: '200px', borderRadius: '8px', background: '#e2e8f0', marginBottom: '24px', animation: 'pulse 1.5s infinite' }} />
            </div>
        }>
            <ProjectsList />
        </Suspense>
    );
}
