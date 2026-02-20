'use client';

import { useState } from 'react';
import { useApp } from '@/context/AppContext';

export default function SearchPage() {
    const { apiFetch, city } = useApp();
    const [query, setQuery] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;
        setLoading(true);
        setResult(null);
        try {
            const res = await apiFetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, city }),
            });
            setResult(res.ok ? await res.json() : { error: 'Query failed.' });
        } catch { setResult({ error: 'Cannot connect to backend.' }); }
        setLoading(false);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
                <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>Search</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Ask about projects in {city === 'delhi' ? 'Delhi' : 'Mumbai'}</p>
            </div>

            <form onSubmit={handleSearch} className="search-bar">
                <input className="input" value={query} onChange={(e) => setQuery(e.target.value)}
                    placeholder="e.g. What projects are delayed in Kandivali?" />
                <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </form>

            {!result && (
                <div className="card">
                    <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px' }}>Try asking:</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {[
                            'Show me road projects in Kandivali',
                            'What projects are delayed?',
                            'What is happening in Bandra?',
                            city === 'delhi' ? 'Show projects in Dwarka' : 'Healthcare projects in Mulund',
                        ].map((q) => (
                            <button key={q} onClick={() => setQuery(q)} style={{
                                textAlign: 'left', padding: '10px 12px', borderRadius: '8px',
                                border: '1px solid var(--border)', background: 'var(--bg)', cursor: 'pointer',
                                fontSize: '13px', color: 'var(--text-secondary)', transition: 'border-color .15s',
                            }}>{q}</button>
                        ))}
                    </div>
                </div>
            )}

            {result && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {result.error ? (
                        <div className="card" style={{ background: 'var(--red-bg)' }}>
                            <p style={{ color: 'var(--red)', fontSize: '14px' }}>{result.error}</p>
                        </div>
                    ) : (
                        <>
                            <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
                                <p style={{ fontSize: '14px', lineHeight: 1.7 }}>{result.answer}</p>
                            </div>
                            {result.projects?.length > 0 && (
                                <div className="card">
                                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>{result.projects_count} projects found</p>
                                    {result.projects.map((p, i) => (
                                        <div key={i} className="project-item">
                                            <div>
                                                <div className="project-name">{p.project_name}</div>
                                                <div className="project-meta">Ward {p.ward_number} – {p.ward_name}{p.budget_amount ? ` · ₹${(p.budget_amount / 100000).toFixed(1)}L` : ''}</div>
                                            </div>
                                            <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                                <span className={`status-badge status-${p.status}`}>{p.status}</span>
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
        </div>
    );
}
