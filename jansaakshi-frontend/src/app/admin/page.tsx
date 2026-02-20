'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApp } from '@/context/AppContext';
import { icons } from '@/components/Navigation';

export default function AdminPage() {
    const { user, isAdmin, apiFetch, city } = useApp();
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState(null);
    const [complaints, setComplaints] = useState([]);
    const [tab, setTab] = useState('upload');

    const loadComplaints = useCallback(async () => {
        try {
            const res = await apiFetch('/api/admin/complaints');
            if (res.ok) setComplaints((await res.json()).complaints || []);
        } catch { }
    }, [apiFetch]);

    useEffect(() => { if (isAdmin && tab === 'complaints') loadComplaints(); }, [isAdmin, tab, loadComplaints]);

    if (!user) {
        return (
            <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <h1 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Admin Panel</h1>
                <p style={{ color: 'var(--text-muted)' }}>Please <a href="/profile" style={{ color: 'var(--primary)' }}>log in</a> with an admin account.</p>
            </div>
        );
    }

    if (!isAdmin) {
        return (
            <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <h1 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Access Denied</h1>
                <p style={{ color: 'var(--text-muted)' }}>This page is for administrators only.</p>
            </div>
        );
    }

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setUploading(true);
        setUploadResult(null);
        const fd = new FormData();
        fd.append('file', file);
        fd.append('city', city);
        try {
            const res = await apiFetch('/api/admin/upload-pdf', { method: 'POST', body: fd });
            setUploadResult(await res.json());
        } catch { setUploadResult({ error: 'Upload failed' }); }
        setUploading(false);
    };

    const updateComplaint = async (id, status, notes) => {
        await apiFetch(`/api/admin/complaints/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, admin_notes: notes }),
        });
        loadComplaints();
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
                <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>Admin Panel</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Manage PDFs and complaints for {city}</p>
            </div>

            <div style={{ display: 'flex', gap: '4px' }}>
                <button className={`btn ${tab === 'upload' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('upload')}>PDF Upload</button>
                <button className={`btn ${tab === 'complaints' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('complaints')}>Complaints</button>
            </div>

            {tab === 'upload' && (
                <div className="card">
                    <h2 className="card-title" style={{ marginBottom: '10px' }}>Upload Meeting PDF</h2>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                        City: <strong>{city}</strong>. The system will extract project details automatically.
                    </p>
                    <label className="upload-zone" style={{ display: 'block' }}>
                        <input type="file" accept=".pdf" onChange={handleUpload} disabled={uploading} style={{ display: 'none' }} />
                        <div style={{ marginBottom: '6px', display: 'flex', justifyContent: 'center', color: 'var(--text-muted)' }}>{icons.shield}</div>
                        <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{uploading ? 'Processing...' : 'Click to select PDF'}</div>
                    </label>

                    {uploadResult && (
                        <div style={{
                            marginTop: '14px', padding: '12px', borderRadius: '8px',
                            background: uploadResult.success ? 'var(--green-bg)' : 'var(--red-bg)',
                            border: `1px solid ${uploadResult.success ? '#bbf7d0' : '#fecaca'}`,
                        }}>
                            <p style={{ fontSize: '14px', fontWeight: 500, color: uploadResult.success ? 'var(--green)' : 'var(--red)' }}>
                                {uploadResult.success ? uploadResult.message : (uploadResult.error || 'Failed')}
                            </p>
                        </div>
                    )}

                    {uploadResult?.projects?.length > 0 && (
                        <div style={{ marginTop: '14px' }}>
                            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Extracted ({uploadResult.projects.length})</h3>
                            {uploadResult.projects.map((p, i) => (
                                <div key={i} className="project-item">
                                    <div>
                                        <div className="project-name">{p.project_name}</div>
                                        <div className="project-meta">Ward {p.ward_no} – {p.ward_name}{p.ward_zone ? ` (${p.ward_zone})` : ''}</div>
                                    </div>
                                    <span className={`status-badge status-${p.status || 'pending'}`}>{p.status || 'pending'}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {tab === 'complaints' && (
                <div className="card">
                    <h2 className="card-title" style={{ marginBottom: '10px' }}>All Complaints ({complaints.length})</h2>
                    {complaints.length === 0 ? (
                        <p style={{ color: 'var(--text-muted)' }}>No complaints.</p>
                    ) : complaints.map((c, i) => (
                        <div key={i} className="project-item" style={{ flexDirection: 'column', gap: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'flex-start' }}>
                                <div>
                                    <div className="project-name">{c.category}</div>
                                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>{c.description}</p>
                                    <div className="project-meta">
                                        Ward {c.ward_no} · {c.citizen_name || 'Anonymous'} · {c.created_at?.split('T')[0]}
                                    </div>
                                </div>
                                <span className={`status-badge ${c.status === 'resolved' ? 'status-completed' : c.status === 'in_progress' ? 'status-ongoing' : 'status-approved'}`}>
                                    {c.status}
                                </span>
                            </div>
                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                <button className="btn btn-outline" style={{ fontSize: '11px', padding: '3px 8px' }}
                                    onClick={() => updateComplaint(c.id, 'in_progress', 'Under review')}>Mark In Progress</button>
                                <button className="btn btn-outline" style={{ fontSize: '11px', padding: '3px 8px' }}
                                    onClick={() => updateComplaint(c.id, 'resolved', 'Issue resolved')}>Mark Resolved</button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
