'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApp } from '@/context/AppContext';

interface Contractor {
    contractor_name: string;
    total_projects: number;
    completed: number;
    delayed: number;
    in_progress: number;
    stalled: number;
    total_budget: number;
    avg_delay_days: number;
    max_delay_days: number;
    wards_count: number;
    project_types: string[];
    delay_pct: number;
    completion_pct: number;
}

interface Project {
    id: number;
    project_name: string;
    status: string;
    ward_no: string;
    ward_name: string;
    budget: number;
    delay_days: number;
    project_type?: string;
    start_date?: string;
    expected_completion?: string;
    location_details?: string;
}

/* ─── small helpers ─────────────────────────────────────────── */

function badgeStyle(color: string, bg: string): React.CSSProperties {
    return {
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '3px 10px', borderRadius: 20, fontSize: 11,
        fontWeight: 700, color, background: bg, whiteSpace: 'nowrap',
    };
}

function PerformanceBadge({ delayPct }: { delayPct: number }) {
    if (delayPct === 0) return <span style={badgeStyle('#16a34a', '#f0fdf4')}>⭐ Excellent</span>;
    if (delayPct < 15) return <span style={badgeStyle('#2563eb', '#eff6ff')}>✓ Good</span>;
    if (delayPct < 35) return <span style={badgeStyle('#d97706', '#fffbeb')}>⚠ Average</span>;
    return <span style={badgeStyle('#dc2626', '#fef2f2')}>✗ Poor</span>;
}

function StatPill({ label, value, color }: { label: string; value: string | number; color?: string }) {
    return (
        <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            padding: '10px 14px', background: '#f8fafc', borderRadius: 10,
            border: '1px solid #e2e8f0', minWidth: 70,
        }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: color || '#1e293b' }}>{value}</span>
            <span style={{ fontSize: 10, color: '#94a3b8', marginTop: 2, textAlign: 'center', lineHeight: 1.3 }}>{label}</span>
        </div>
    );
}

function RadialProgress({ value, color, size = 52 }: { value: number; color: string; size?: number }) {
    const r = (size - 8) / 2;
    const circ = 2 * Math.PI * r;
    const dash = (value / 100) * circ;
    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={6} />
            <circle
                cx={size / 2} cy={size / 2} r={r} fill="none"
                stroke={color} strokeWidth={6}
                strokeDasharray={`${dash} ${circ - dash}`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
        </svg>
    );
}

function ProgressBar({ segments }: {
    segments: { value: number; total: number; color: string; label: string }[]
}) {
    const total = segments[0]?.total || 1;
    return (
        <div>
            <div style={{ display: 'flex', borderRadius: 4, overflow: 'hidden', height: 6, background: '#f1f5f9' }}>
                {segments.map((s, i) =>
                    s.value > 0 ? (
                        <div key={i} title={s.label}
                            style={{ width: `${(s.value / total) * 100}%`, background: s.color, transition: 'width .6s ease' }}
                        />
                    ) : null
                )}
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
                {segments.filter(s => s.value > 0).map((s, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color }} />
                        <span style={{ fontSize: 10, color: '#64748b' }}>{s.label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const map: Record<string, { bg: string; color: string }> = {
        completed: { bg: '#f0fdf4', color: '#16a34a' },
        delayed: { bg: '#fef2f2', color: '#dc2626' },
        'in progress': { bg: '#fffbeb', color: '#d97706' },
        stalled: { bg: '#f5f3ff', color: '#7c3aed' },
    };
    const s = map[(status || '').toLowerCase()] || { bg: '#eff6ff', color: '#2563eb' };
    return (
        <span style={{
            display: 'inline-block', padding: '2px 9px', borderRadius: 20,
            fontSize: 11, fontWeight: 600, background: s.bg, color: s.color, whiteSpace: 'nowrap',
        }}>{status || 'unknown'}</span>
    );
}

/* ─── ProjectPanel – self-contained, fetches its own data ───── */

function ProjectPanel({ contractorName, apiFetch }: {
    contractorName: string;
    apiFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
    const [projects, setProjects] = useState<Project[] | null>(null); // null = loading
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        setProjects(null);
        setError(null);

        // Use query param – avoids all URL encoding / Flask routing issues
        apiFetch(`/api/contractor-projects?name=${encodeURIComponent(contractorName)}`)
            .then(async res => {
                if (cancelled) return;
                if (!res.ok) { setError(`Server error ${res.status}`); return; }
                const data = await res.json();
                if (!cancelled) setProjects(data.projects ?? []);
            })
            .catch(err => {
                if (!cancelled) setError(err.message || 'Network error');
            });

        return () => { cancelled = true; };
    }, [contractorName, apiFetch]);

    if (error) return (
        <div style={{ padding: '20px 0', textAlign: 'center', color: '#dc2626', fontSize: 13 }}>
            ⚠ Could not load projects: {error}
        </div>
    );

    if (projects === null) return (
        <div style={{ padding: '24px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>⏳</div>
            Loading projects…
        </div>
    );

    if (projects.length === 0) return (
        <div style={{ padding: '24px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>📭</div>
            No project details found for this contractor.
        </div>
    );

    return (
        <>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '.5px' }}>
                {projects.length} Project{projects.length !== 1 ? 's' : ''}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {projects.map(p => (
                    <div key={p.id} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                        background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0',
                        padding: '12px 14px', gap: 12,
                    }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: 13, color: '#0f172a', marginBottom: 4 }}>
                                {p.project_name}
                            </div>
                            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                                <span>Ward {p.ward_no}{p.ward_name ? ` · ${p.ward_name}` : ''}</span>
                                {p.project_type && <span>· {p.project_type}</span>}
                                {p.budget > 0 && <span>· ₹{(p.budget / 100000).toFixed(1)}L</span>}
                                {p.location_details && <span>· {p.location_details}</span>}
                            </div>
                            {(p.start_date || p.expected_completion) && (
                                <div style={{ fontSize: 10, color: '#b0bec5', marginTop: 3 }}>
                                    {p.start_date && <>Start: {p.start_date}</>}
                                    {p.start_date && p.expected_completion && ' → '}
                                    {p.expected_completion && <>Due: {p.expected_completion}</>}
                                </div>
                            )}
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                            <StatusBadge status={p.status} />
                            {p.delay_days > 0 && (
                                <div style={{ fontSize: 11, color: '#dc2626', fontWeight: 700, marginTop: 4 }}>
                                    {p.delay_days}d overdue
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </>
    );
}

/* ─── Main page ─────────────────────────────────────────────── */

export default function ContractorsPage() {
    const { apiFetch, city } = useApp();
    const [contractors, setContractors] = useState<Contractor[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [sortBy, setSortBy] = useState<'total' | 'delay' | 'completion' | 'budget'>('total');
    // Set of expanded contractor names – can open multiple
    const [expanded, setExpanded] = useState<Set<string>>(new Set());

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await apiFetch('/api/contractors');
            if (res.ok) {
                const data = await res.json();
                setContractors(data.contractors || []);
            }
        } finally {
            setLoading(false);
        }
    }, [apiFetch]);

    useEffect(() => { load(); }, [load]);

    const toggleExpand = (name: string) => {
        setExpanded(prev => {
            const next = new Set(prev);
            if (next.has(name)) next.delete(name);
            else next.add(name);
            return next;
        });
    };

    const filtered = contractors
        .filter(c => c.contractor_name.toLowerCase().includes(search.toLowerCase()))
        .sort((a, b) => {
            if (sortBy === 'delay') return b.delay_pct - a.delay_pct;
            if (sortBy === 'completion') return b.completion_pct - a.completion_pct;
            if (sortBy === 'budget') return b.total_budget - a.total_budget;
            return b.total_projects - a.total_projects;
        });

    const cityLabel = city === 'delhi' ? 'Delhi' : 'Mumbai';

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* ── Header ── */}
            <div style={{
                background: 'linear-gradient(135deg, #1d4ed8 0%, #0f172a 100%)',
                borderRadius: 14, padding: '28px 28px 24px',
                color: '#fff', position: 'relative', overflow: 'hidden',
            }}>
                <div style={{ position: 'absolute', top: -30, right: -30, width: 160, height: 160, borderRadius: '50%', background: 'rgba(255,255,255,0.04)' }} />
                <div style={{ position: 'absolute', bottom: -40, left: '40%', width: 200, height: 200, borderRadius: '50%', background: 'rgba(255,255,255,0.03)' }} />
                <div style={{ position: 'relative' }}>
                    <div style={{ fontSize: 28, marginBottom: 4 }}>🏗️</div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 6, letterSpacing: '-0.3px' }}>
                        Contractor Directory
                    </h1>
                    <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)', marginBottom: 16, maxWidth: 480 }}>
                        Track accountability records for every contractor on municipal projects in {cityLabel}.
                        Click any card to see their full project history.
                    </p>
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                        {[
                            [contractors.length, 'Contractors'],
                            [contractors.reduce((s, c) => s + c.total_projects, 0), 'Projects'],
                            [contractors.filter(c => c.delayed > 0).length, 'With Delays'],
                        ].map(([val, lbl]) => (
                            <div key={lbl as string} style={{ background: 'rgba(255,255,255,0.1)', borderRadius: 8, padding: '8px 16px' }}>
                                <span style={{ fontSize: 20, fontWeight: 700 }}>{val}</span>
                                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', marginLeft: 6 }}>{lbl}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Search + Sort ── */}
            <div style={{
                display: 'flex', gap: 10, flexWrap: 'wrap',
                background: '#fff', border: '1px solid #e2e8f0',
                borderRadius: 12, padding: '14px 16px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
            }}>
                <input
                    id="contractor-search"
                    className="input"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="🔍  Search contractor by name…"
                    style={{ flex: 1, minWidth: 200 }}
                />
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {([
                        ['total', 'Most Projects'],
                        ['delay', 'Highest Delay %'],
                        ['completion', 'Most Complete'],
                        ['budget', 'Highest Budget'],
                    ] as const).map(([key, label]) => (
                        <button key={key} onClick={() => setSortBy(key)} style={{
                            padding: '8px 14px', borderRadius: 8, border: '1px solid',
                            fontSize: 12, fontWeight: 600, cursor: 'pointer', transition: 'all .15s',
                            borderColor: sortBy === key ? '#1d4ed8' : '#e2e8f0',
                            background: sortBy === key ? '#eff6ff' : '#fff',
                            color: sortBy === key ? '#1d4ed8' : '#64748b',
                        }}>{label}</button>
                    ))}
                </div>
            </div>

            {/* ── Cards ── */}
            {loading ? (
                <div className="card" style={{ textAlign: 'center', padding: 48, color: '#94a3b8' }}>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>⏳</div>
                    <p>Loading contractor data…</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48, color: '#94a3b8' }}>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>🔍</div>
                    <p>No contractors found{search ? ` for "${search}"` : ''}.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {filtered.map((c, idx) => {
                        const isOpen = expanded.has(c.contractor_name);
                        return (
                            <div key={c.contractor_name} style={{
                                background: '#fff', border: '1px solid',
                                borderColor: isOpen ? '#93c5fd' : '#e2e8f0',
                                borderRadius: 14, overflow: 'hidden',
                                boxShadow: isOpen ? '0 4px 16px rgba(29,78,216,0.10)' : '0 1px 3px rgba(0,0,0,0.05)',
                                transition: 'box-shadow .2s, border-color .2s',
                            }}>
                                {/* ── Card summary row ── */}
                                <div
                                    id={`contractor-${idx}`}
                                    onClick={() => toggleExpand(c.contractor_name)}
                                    style={{
                                        padding: '18px 20px', cursor: 'pointer', userSelect: 'none',
                                        display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
                                    }}
                                >
                                    {/* Rank avatar */}
                                    <div style={{
                                        width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                                        background: idx === 0 ? 'linear-gradient(135deg,#fbbf24,#f59e0b)'
                                            : idx === 1 ? 'linear-gradient(135deg,#94a3b8,#64748b)'
                                                : idx === 2 ? 'linear-gradient(135deg,#c084fc,#a855f7)'
                                                    : 'linear-gradient(135deg,#60a5fa,#1d4ed8)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        color: '#fff', fontWeight: 800, fontSize: 16,
                                    }}>
                                        {idx < 3 ? ['🥇', '🥈', '🥉'][idx] : (idx + 1)}
                                    </div>

                                    {/* Name + types */}
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a', marginBottom: 3 }}>
                                            {c.contractor_name}
                                        </div>
                                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                                            <PerformanceBadge delayPct={c.delay_pct} />
                                            {c.project_types.slice(0, 3).map(t => (
                                                <span key={t} style={{
                                                    padding: '2px 8px', borderRadius: 20, fontSize: 10,
                                                    background: '#f1f5f9', color: '#475569', fontWeight: 500,
                                                }}>{t}</span>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Radial rings */}
                                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                                        {[
                                            { val: c.completion_pct, color: '#16a34a', label: 'Done' },
                                            { val: c.delay_pct, color: c.delay_pct > 35 ? '#dc2626' : c.delay_pct > 15 ? '#d97706' : '#2563eb', label: 'Delayed' },
                                        ].map(({ val, color, label }) => (
                                            <div key={label} style={{ textAlign: 'center' }}>
                                                <div style={{ position: 'relative', display: 'inline-block' }}>
                                                    <RadialProgress value={val} color={color} />
                                                    <span style={{
                                                        position: 'absolute', top: '50%', left: '50%',
                                                        transform: 'translate(-50%,-50%) rotate(90deg)',
                                                        fontSize: 10, fontWeight: 700, color,
                                                    }}>{val}%</span>
                                                </div>
                                                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>{label}</div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Stat pills */}
                                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                        <StatPill label="Projects" value={c.total_projects} color="#1d4ed8" />
                                        <StatPill label="Wards" value={c.wards_count} />
                                        <StatPill label="Budget" value={c.total_budget > 0 ? `₹${(c.total_budget / 10000000).toFixed(1)}Cr` : '—'} />
                                        {c.avg_delay_days > 0 && (
                                            <StatPill label="Avg Delay" value={`${Math.round(c.avg_delay_days)}d`} color="#dc2626" />
                                        )}
                                    </div>

                                    {/* Expand arrow */}
                                    <div style={{
                                        fontSize: 18, color: isOpen ? '#1d4ed8' : '#94a3b8',
                                        transition: 'transform .2s, color .2s',
                                        transform: isOpen ? 'rotate(180deg)' : 'none',
                                        flexShrink: 0,
                                    }}>▾</div>
                                </div>

                                {/* Progress bar */}
                                <div style={{ padding: '0 20px 14px' }}>
                                    <ProgressBar segments={[
                                        { value: c.completed, total: c.total_projects, color: '#22c55e', label: `${c.completed} Completed` },
                                        { value: c.in_progress, total: c.total_projects, color: '#f59e0b', label: `${c.in_progress} In Progress` },
                                        { value: c.delayed, total: c.total_projects, color: '#ef4444', label: `${c.delayed} Delayed` },
                                        { value: c.stalled, total: c.total_projects, color: '#a855f7', label: `${c.stalled} Stalled` },
                                    ]} />
                                </div>

                                {/* ── Expanded detail panel ── */}
                                {isOpen && (
                                    <div style={{
                                        borderTop: '1px solid #e0ecff',
                                        background: '#f5f8ff',
                                        padding: '20px 20px 20px',
                                        animation: 'fadeIn .18s ease',
                                    }}>
                                        {/* ProjectPanel manages its own fetch lifecycle */}
                                        <ProjectPanel
                                            contractorName={c.contractor_name}
                                            apiFetch={apiFetch}
                                        />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-8px); }
                    to   { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
