'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApp } from '@/context/AppContext';

const categories = [
    'Road Damage', 'Water Supply', 'Sewage / Drainage', 'Streetlights',
    'Garbage Collection', 'Noise Pollution', 'Illegal Construction', 'Public Safety', 'Other',
];

export default function ComplaintsPage() {
    const { user, apiFetch, city } = useApp();
    const [complaints, setComplaints] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [form, setForm] = useState({
        ward_no: user?.ward || '', category: '', description: '',
        location: '', citizen_name: user?.display_name || '', user_phone: '',
    });

    const loadComplaints = useCallback(async () => {
        try {
            const res = await apiFetch('/api/complaints');
            if (res.ok) setComplaints((await res.json()).complaints || []);
        } catch { }
    }, [apiFetch]);

    useEffect(() => { loadComplaints(); }, [loadComplaints]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.category || !form.description) return;
        setSubmitting(true);
        try {
            const res = await apiFetch('/api/complaints', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...form, city }),
            });
            if (res.ok) {
                setSubmitted(true);
                setTimeout(() => { setSubmitted(false); setShowForm(false); loadComplaints(); }, 1500);
                setForm({ ward_no: user?.ward || '', category: '', description: '', location: '', citizen_name: user?.display_name || '', user_phone: '' });
            }
        } catch { }
        setSubmitting(false);
    };

    const statusLabel = (s) => {
        if (s === 'resolved') return 'status-completed';
        if (s === 'in_progress') return 'status-ongoing';
        return 'status-approved';
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>Complaints</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {user ? 'Your submitted complaints' : 'Log in to track your complaints'}
                    </p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
                    {showForm ? 'Cancel' : 'New Complaint'}
                </button>
            </div>

            {showForm && (
                <form onSubmit={handleSubmit} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {submitted ? (
                        <p style={{ textAlign: 'center', color: 'var(--green)', fontWeight: 600, padding: '16px' }}>Complaint submitted!</p>
                    ) : (
                        <>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                <div>
                                    <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '3px' }}>Name</label>
                                    <input className="input" value={form.citizen_name} onChange={(e) => setForm({ ...form, citizen_name: e.target.value })} />
                                </div>
                                <div>
                                    <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '3px' }}>Phone</label>
                                    <input className="input" value={form.user_phone} onChange={(e) => setForm({ ...form, user_phone: e.target.value })} placeholder="Optional" />
                                </div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                <div>
                                    <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '3px' }}>Ward No.</label>
                                    <input className="input" value={form.ward_no} onChange={(e) => setForm({ ...form, ward_no: e.target.value })} placeholder="e.g. 77" />
                                </div>
                                <div>
                                    <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '3px' }}>Category *</label>
                                    <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required>
                                        <option value="">Select</option>
                                        {categories.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '3px' }}>Location</label>
                                <input className="input" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Street, landmark" />
                            </div>
                            <div>
                                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '3px' }}>Description *</label>
                                <textarea className="input textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required placeholder="Describe the issue..." />
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit'}</button>
                        </>
                    )}
                </form>
            )}

            <div className="card">
                <h2 className="card-title" style={{ marginBottom: '10px' }}>
                    {user ? 'Your Complaints' : 'Recent Complaints'}
                </h2>
                {complaints.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                        {user ? 'No complaints submitted yet.' : 'Log in to see your complaints.'}
                    </p>
                ) : complaints.map((c, i) => (
                    <div key={i} className="project-item">
                        <div>
                            <div className="project-name">{c.category}</div>
                            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>{c.description}</p>
                            <div className="project-meta">
                                {c.ward_no ? `Ward ${c.ward_no}` : ''}{c.location ? ` · ${c.location}` : ''}
                                {c.created_at ? ` · ${c.created_at.split('T')[0]}` : ''}
                            </div>
                            {c.admin_notes && <p style={{ fontSize: '12px', color: 'var(--primary)', marginTop: '4px' }}>Admin: {c.admin_notes}</p>}
                        </div>
                        <span className={`status-badge ${statusLabel(c.status)}`}>{c.status}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
