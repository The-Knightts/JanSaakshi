'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApp } from '@/context/AppContext';

export default function ProjectsPage() {
    const { apiFetch } = useApp();
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState({ status: '', type: '', q: '' });

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filter.status) params.set('status', filter.status);
            if (filter.type) params.set('type', filter.type);
            if (filter.q) params.set('q', filter.q);
            const res = await apiFetch(`/api/projects?${params}`);
            if (res.ok) setProjects((await res.json()).projects || []);
        } catch { }
        setLoading(false);
    }, [filter, apiFetch]);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
                <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>Projects</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>All municipal projects in your city</p>
            </div>

            <div className="card" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
                <input className="input" placeholder="Search projects..." value={filter.q}
                    onChange={(e) => setFilter({ ...filter, q: e.target.value })} style={{ maxWidth: '300px' }} />
                <select className="input" value={filter.status}
                    onChange={(e) => setFilter({ ...filter, status: e.target.value })} style={{ maxWidth: '150px' }}>
                    <option value="">All Status</option>
                    <option value="delayed">Delayed</option>
                    <option value="ongoing">Ongoing</option>
                    <option value="completed">Completed</option>
                    <option value="stalled">Stalled</option>
                    <option value="approved">Approved</option>
                </select>
                <select className="input" value={filter.type}
                    onChange={(e) => setFilter({ ...filter, type: e.target.value })} style={{ maxWidth: '170px' }}>
                    <option value="">All Types</option>
                    <option value="roads">Roads</option>
                    <option value="water_supply">Water Supply</option>
                    <option value="drainage">Drainage</option>
                    <option value="parks">Parks</option>
                    <option value="schools">Schools</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="street_lighting">Street Lighting</option>
                    <option value="waste_management">Waste Management</option>
                </select>
                <button className="btn btn-primary" onClick={load}>Filter</button>
            </div>

            <div className="card">
                {loading ? (
                    <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
                ) : projects.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)' }}>No projects found.</p>
                ) : (
                    <>
                        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>{projects.length} projects</p>
                        {projects.map((p, i) => (
                            <div key={i} className="project-item">
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div className="project-name">{p.project_name}</div>
                                    {p.summary && <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '3px', lineHeight: 1.5 }}>{p.summary}</p>}
                                    <div className="project-meta" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '5px' }}>
                                        <span>Ward {p.ward_no} – {p.ward_name}{p.ward_zone ? ` (${p.ward_zone})` : ''}</span>
                                        {p.budget && <span>₹{(p.budget / 100000).toFixed(1)}L</span>}
                                        {p.contractor_name && <span>{p.contractor_name}</span>}
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '12px' }}>
                                    <span className={`status-badge status-${p.status || 'pending'}`}>{p.status || 'pending'}</span>
                                    {p.delay_days > 0 && <div style={{ fontSize: '12px', color: 'var(--red)', marginTop: '3px', fontWeight: 600 }}>{p.delay_days}d late</div>}
                                </div>
                            </div>
                        ))}
                    </>
                )}
            </div>
        </div>
    );
}
