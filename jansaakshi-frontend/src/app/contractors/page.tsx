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

interface Review {
    id: number;
    contractor_name: string;
    reviewer_id: number;
    rating: number;
    title?: string;
    body?: string;
    display_name: string;
    username: string;
    created_at: string;
}

interface ReviewData {
    reviews: Review[];
    avg_rating: number;
    review_count: number;
    user_review: { id: number; rating: number } | null;
}

/* ─── Helpers ───────────────────────────────────────────────── */

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

/* ─── StarRating ─────────────────────────────────────────────── */

function StarRating({ value, onChange, readOnly = false, size = 22 }: {
    value: number;
    onChange?: (v: number) => void;
    readOnly?: boolean;
    size?: number;
}) {
    const [hovered, setHovered] = useState(0);
    const display = hovered || value;
    return (
        <div style={{ display: 'flex', gap: 2 }}>
            {[1, 2, 3, 4, 5].map(star => (
                <span
                    key={star}
                    onClick={() => !readOnly && onChange?.(star)}
                    onMouseEnter={() => !readOnly && setHovered(star)}
                    onMouseLeave={() => !readOnly && setHovered(0)}
                    style={{
                        fontSize: size, cursor: readOnly ? 'default' : 'pointer',
                        color: star <= display ? '#f59e0b' : '#e2e8f0',
                        transition: 'color .1s',
                        userSelect: 'none',
                    }}
                >★</span>
            ))}
        </div>
    );
}

/* ─── RatingBar — shows distribution ────────────────────────── */

function RatingDistribution({ reviews }: { reviews: Review[] }) {
    const counts = [5, 4, 3, 2, 1].map(star => ({
        star,
        count: reviews.filter(r => r.rating === star).length,
    }));
    const max = Math.max(...counts.map(c => c.count), 1);
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 140 }}>
            {counts.map(({ star, count }) => (
                <div key={star} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 11, color: '#64748b', width: 8 }}>{star}</span>
                    <span style={{ fontSize: 12, color: '#f59e0b' }}>★</span>
                    <div style={{ flex: 1, height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{
                            height: '100%', borderRadius: 3,
                            background: '#f59e0b',
                            width: `${(count / max) * 100}%`,
                            transition: 'width .4s ease',
                        }} />
                    </div>
                    <span style={{ fontSize: 11, color: '#94a3b8', width: 16, textAlign: 'right' }}>{count}</span>
                </div>
            ))}
        </div>
    );
}

/* ─── ReviewCard ─────────────────────────────────────────────── */

function ReviewCard({ review }: { review: Review }) {
    const initials = (review.display_name || review.username || '?').slice(0, 2).toUpperCase();
    return (
        <div style={{
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
            padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 6,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                    width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
                    background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontWeight: 700, fontSize: 12,
                }}>{initials}</div>
                <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#0f172a' }}>
                        {review.display_name || review.username}
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>
                        {review.created_at ? review.created_at.slice(0, 10) : ''}
                    </div>
                </div>
                <StarRating value={review.rating} readOnly size={16} />
            </div>
            {review.title && (
                <div style={{ fontWeight: 600, fontSize: 13, color: '#1e293b' }}>{review.title}</div>
            )}
            {review.body && (
                <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.6, margin: 0 }}>{review.body}</p>
            )}
        </div>
    );
}

/* ─── ReviewPanel ────────────────────────────────────────────── */

function ReviewPanel({ contractorName, apiFetch, isAuthorizedUser, user }: {
    contractorName: string;
    apiFetch: (url: string, opts?: RequestInit) => Promise<Response>;
    isAuthorizedUser: boolean;
    user: any;
}) {
    const [data, setData] = useState<ReviewData | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({ rating: 0, title: '', body: '' });
    const [submitMsg, setSubmitMsg] = useState<{ ok: boolean; text: string } | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await apiFetch(`/api/contractors/reviews?name=${encodeURIComponent(contractorName)}`);
            if (res.ok) {
                const d = await res.json();
                setData(d);
                if (d.user_review) {
                    setForm(prev => ({ ...prev, rating: d.user_review.rating }));
                }
            }
        } finally {
            setLoading(false);
        }
    }, [contractorName, apiFetch]);

    useEffect(() => { load(); }, [load]);

    const handleSubmit = async () => {
        if (form.rating < 1) { setSubmitMsg({ ok: false, text: 'Please select a star rating.' }); return; }
        setSubmitting(true);
        setSubmitMsg(null);
        try {
            const res = await apiFetch('/api/contractors/reviews', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contractor_name: contractorName,
                    rating: form.rating,
                    title: form.title || undefined,
                    body: form.body || undefined,
                }),
            });
            const d = await res.json();
            if (d.success) {
                setSubmitMsg({ ok: true, text: 'Review submitted! Thank you.' });
                setShowForm(false);
                load();
            } else {
                setSubmitMsg({ ok: false, text: d.error || 'Submission failed.' });
            }
        } catch {
            setSubmitMsg({ ok: false, text: 'Network error.' });
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return (
        <div style={{ padding: '20px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
            Loading reviews…
        </div>
    );

    const reviews = data?.reviews ?? [];
    const avgRating = data?.avg_rating ?? 0;
    const reviewCount = data?.review_count ?? 0;
    const alreadyReviewed = !!data?.user_review;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 8 }}>
            {/* ── Header row ── */}
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                flexWrap: 'wrap', gap: 12,
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                    {/* Big score */}
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 40, fontWeight: 800, color: '#0f172a', lineHeight: 1 }}>
                            {avgRating > 0 ? avgRating.toFixed(1) : '—'}
                        </div>
                        <StarRating value={Math.round(avgRating)} readOnly size={18} />
                        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                            {reviewCount} review{reviewCount !== 1 ? 's' : ''}
                        </div>
                    </div>
                    {reviews.length > 0 && <RatingDistribution reviews={reviews} />}
                </div>

                {/* Write / Edit review button */}
                {isAuthorizedUser && (
                    <button
                        onClick={() => { setShowForm(f => !f); setSubmitMsg(null); }}
                        style={{
                            padding: '9px 18px', borderRadius: 8, border: '1.5px solid #2563eb',
                            background: showForm ? '#eff6ff' : '#2563eb', cursor: 'pointer',
                            color: showForm ? '#2563eb' : '#fff', fontWeight: 600, fontSize: 13,
                            transition: 'all .15s',
                        }}
                    >
                        {showForm ? 'Cancel' : alreadyReviewed ? '✏ Edit Your Review' : '★ Write a Review'}
                    </button>
                )}
                {!isAuthorizedUser && !user && (
                    <div style={{
                        fontSize: 12, color: '#94a3b8', padding: '8px 14px',
                        background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0',
                    }}>
                        🔒 Log in as an authorized reviewer to rate this contractor
                    </div>
                )}
                {!isAuthorizedUser && user && (
                    <div style={{
                        fontSize: 12, color: '#94a3b8', padding: '8px 14px',
                        background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0',
                    }}>
                        🔒 Only authorized users & admins can submit reviews
                    </div>
                )}
            </div>

            {/* ── Review form ── */}
            {showForm && isAuthorizedUser && (
                <div style={{
                    background: '#fff', border: '1.5px solid #bfdbfe', borderRadius: 12,
                    padding: '18px 18px', display: 'flex', flexDirection: 'column', gap: 14,
                    boxShadow: '0 2px 8px rgba(37,99,235,0.08)',
                }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b' }}>
                        {alreadyReviewed ? 'Update your review' : 'Share your experience'}
                    </div>

                    <div>
                        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, fontWeight: 500 }}>Your Rating *</div>
                        <StarRating value={form.rating} onChange={v => setForm(f => ({ ...f, rating: v }))} size={28} />
                    </div>

                    <div>
                        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4, fontWeight: 500 }}>Title (optional)</div>
                        <input
                            className="input"
                            value={form.title}
                            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                            placeholder="Summarize your experience…"
                        />
                    </div>

                    <div>
                        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4, fontWeight: 500 }}>Review (optional)</div>
                        <textarea
                            className="input"
                            value={form.body}
                            onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
                            placeholder="Describe contractor performance, punctuality, quality…"
                            rows={4}
                            style={{ resize: 'vertical', fontFamily: 'inherit' }}
                        />
                    </div>

                    {submitMsg && (
                        <div style={{
                            padding: '8px 12px', borderRadius: 8, fontSize: 13,
                            background: submitMsg.ok ? '#f0fdf4' : '#fef2f2',
                            color: submitMsg.ok ? '#16a34a' : '#dc2626',
                            border: `1px solid ${submitMsg.ok ? '#bbf7d0' : '#fecaca'}`,
                        }}>{submitMsg.text}</div>
                    )}

                    <button
                        onClick={handleSubmit}
                        disabled={submitting || form.rating < 1}
                        style={{
                            padding: '10px 20px', borderRadius: 8, border: 'none',
                            background: form.rating > 0 ? '#2563eb' : '#e2e8f0',
                            color: form.rating > 0 ? '#fff' : '#94a3b8',
                            fontWeight: 700, fontSize: 13, cursor: form.rating > 0 ? 'pointer' : 'not-allowed',
                            alignSelf: 'flex-start', transition: 'background .15s',
                        }}
                    >
                        {submitting ? 'Submitting…' : alreadyReviewed ? 'Update Review' : 'Submit Review'}
                    </button>
                </div>
            )}

            {/* ── Reviews list ── */}
            {reviews.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px 0', color: '#94a3b8', fontSize: 13 }}>
                    📝 No reviews yet. Be the first to rate this contractor!
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {reviews.map(r => <ReviewCard key={r.id} review={r} />)}
                </div>
            )}
        </div>
    );
}

/* ─── ProjectPanel ───────────────────────────────────────────── */

function ProjectPanel({ contractorName, apiFetch }: {
    contractorName: string;
    apiFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
    const [projects, setProjects] = useState<Project[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        setProjects(null);
        setError(null);
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
            <div style={{ fontSize: 24, marginBottom: 6 }}>⏳</div>Loading projects…
        </div>
    );
    if (projects.length === 0) return (
        <div style={{ padding: '24px 0', textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>📭</div>No project details found.
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
                            <div style={{ fontWeight: 600, fontSize: 13, color: '#0f172a', marginBottom: 4 }}>{p.project_name}</div>
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

type ExpandedTab = 'projects' | 'reviews';

export default function ContractorsPage() {
    const { apiFetch, city, isAuthorizedUser, user } = useApp();
    const [contractors, setContractors] = useState<Contractor[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [sortBy, setSortBy] = useState<'total' | 'delay' | 'completion' | 'budget'>('total');
    const [expanded, setExpanded] = useState<Map<string, ExpandedTab>>(new Map());

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

    const toggleExpand = (name: string, tab: ExpandedTab = 'projects') => {
        setExpanded(prev => {
            const next = new Map(prev);
            if (next.has(name) && next.get(name) === tab) {
                next.delete(name);
            } else {
                next.set(name, tab);
            }
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
                    <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)', marginBottom: 16, maxWidth: 500 }}>
                        Track accountability records and community reviews for every contractor on municipal projects in {cityLabel}.
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
                        const activeTab = expanded.get(c.contractor_name);
                        const isOpen = !!activeTab;
                        return (
                            <div key={c.contractor_name} style={{
                                background: '#fff', border: '1px solid',
                                borderColor: isOpen ? '#93c5fd' : '#e2e8f0',
                                borderRadius: 14, overflow: 'hidden',
                                boxShadow: isOpen ? '0 4px 16px rgba(29,78,216,0.10)' : '0 1px 3px rgba(0,0,0,0.05)',
                                transition: 'box-shadow .2s, border-color .2s',
                            }}>
                                {/* ── Summary row ── */}
                                <div
                                    id={`contractor-${idx}`}
                                    onClick={() => toggleExpand(c.contractor_name, 'projects')}
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

                                {/* ── Progress bar ── */}
                                <div style={{ padding: '0 20px 14px' }}>
                                    <ProgressBar segments={[
                                        { value: c.completed, total: c.total_projects, color: '#22c55e', label: `${c.completed} Completed` },
                                        { value: c.in_progress, total: c.total_projects, color: '#f59e0b', label: `${c.in_progress} In Progress` },
                                        { value: c.delayed, total: c.total_projects, color: '#ef4444', label: `${c.delayed} Delayed` },
                                        { value: c.stalled, total: c.total_projects, color: '#a855f7', label: `${c.stalled} Stalled` },
                                    ]} />
                                </div>

                                {/* ── Expanded panel ── */}
                                {isOpen && (
                                    <div style={{
                                        borderTop: '1px solid #e0ecff',
                                        background: '#f5f8ff',
                                        animation: 'fadeIn .18s ease',
                                    }}>
                                        {/* Tab strip */}
                                        <div style={{
                                            display: 'flex', borderBottom: '1px solid #e0ecff',
                                            background: '#eef2ff',
                                        }}>
                                            {([
                                                ['projects', '📋 Projects'],
                                                ['reviews', '⭐ Reviews'],
                                            ] as [ExpandedTab, string][]).map(([tab, label]) => (
                                                <button
                                                    key={tab}
                                                    onClick={e => { e.stopPropagation(); toggleExpand(c.contractor_name, tab === activeTab ? tab : tab); setExpanded(prev => { const n = new Map(prev); n.set(c.contractor_name, tab); return n; }); }}
                                                    style={{
                                                        padding: '10px 18px', border: 'none', cursor: 'pointer',
                                                        fontSize: 13, fontWeight: 600,
                                                        background: activeTab === tab ? '#fff' : 'transparent',
                                                        color: activeTab === tab ? '#1d4ed8' : '#64748b',
                                                        borderBottom: activeTab === tab ? '2px solid #1d4ed8' : '2px solid transparent',
                                                        transition: 'all .15s',
                                                    }}
                                                >{label}</button>
                                            ))}
                                        </div>

                                        <div style={{ padding: '20px 20px' }}>
                                            {activeTab === 'projects' && (
                                                <ProjectPanel contractorName={c.contractor_name} apiFetch={apiFetch} />
                                            )}
                                            {activeTab === 'reviews' && (
                                                <ReviewPanel
                                                    contractorName={c.contractor_name}
                                                    apiFetch={apiFetch}
                                                    isAuthorizedUser={isAuthorizedUser}
                                                    user={user}
                                                />
                                            )}
                                        </div>
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
