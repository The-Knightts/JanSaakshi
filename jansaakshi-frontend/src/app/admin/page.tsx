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
    const [promoteUsername, setPromoteUsername] = useState('');
    const [promoteRole, setPromoteRole] = useState('authorized_user');
    const [promoteResult, setPromoteResult] = useState<{ ok: boolean; text: string } | null>(null);
    const [promoting, setPromoting] = useState(false);

    const loadComplaints = useCallback(async () => {
        try {
            const res = await apiFetch('/api/admin/complaints');
            if (res.ok) setComplaints((await res.json()).complaints || []);
        } catch { }
    }, [apiFetch]);

    const handlePromote = async () => {
        if (!promoteUsername.trim()) return;
        setPromoting(true);
        setPromoteResult(null);
        try {
            const res = await apiFetch('/api/admin/promote-user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: promoteUsername.trim(), role: promoteRole }),
            });
            const d = await res.json();
            if (d.success) {
                setPromoteResult({ ok: true, text: `@${d.username} is now "${d.new_role}"` });
                setPromoteUsername('');
            } else {
                setPromoteResult({ ok: false, text: d.error || 'Failed.' });
            }
        } catch { setPromoteResult({ ok: false, text: 'Network error.' }); }
        setPromoting(false);
    };


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

            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                <button className={`btn ${tab === 'upload' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('upload')}>PDF Upload</button>
                <button className={`btn ${tab === 'complaints' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('complaints')}>Complaints</button>
                <button className={`btn ${tab === 'users' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('users')}>👤 Manage Users</button>
            </div>

            {tab === 'upload' && (
                <div className="card">
                    <h2 className="card-title" style={{ marginBottom: '10px' }}>Upload Meeting PDF</h2>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                        City: <strong>{city}</strong>. Extracts meeting details + project data automatically.
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

                    {/* Extracted Meeting Details */}
                    {uploadResult?.meeting && Object.keys(uploadResult.meeting).length > 0 && (
                        <div style={{ marginTop: '14px', padding: '14px', borderRadius: '8px', background: 'var(--primary-light)', border: '1px solid #bfdbfe' }}>
                            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px', color: 'var(--primary)' }}>
                                📋 Meeting Details Extracted
                            </h3>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                                {uploadResult.meeting.meet_date && (
                                    <div><strong>Date:</strong> {uploadResult.meeting.meet_date}</div>
                                )}
                                {uploadResult.meeting.meet_type && (
                                    <div><strong>Type:</strong> {uploadResult.meeting.meet_type.replace('_', ' ')}</div>
                                )}
                                {uploadResult.meeting.ward_no && (
                                    <div><strong>Ward:</strong> {uploadResult.meeting.ward_no}{uploadResult.meeting.ward_name ? ` — ${uploadResult.meeting.ward_name}` : ''}</div>
                                )}
                                {uploadResult.meeting.venue && (
                                    <div><strong>Venue:</strong> {uploadResult.meeting.venue}</div>
                                )}
                            </div>
                            {uploadResult.meeting.objective && (
                                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: 1.5 }}>
                                    <strong>Objective:</strong> {uploadResult.meeting.objective}
                                </p>
                            )}
                            {uploadResult.meeting.attendees && (
                                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                                    <strong>Attendees:</strong> {uploadResult.meeting.attendees}
                                </p>
                            )}
                        </div>
                    )}

                    {uploadResult?.projects?.length > 0 && (
                        <div style={{ marginTop: '14px' }}>
                            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Projects Extracted ({uploadResult.projects.length})</h3>
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
            {tab === 'users' && (
                <div className="card">
                    <h2 className="card-title" style={{ marginBottom: '6px' }}>Manage User Roles</h2>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                        Promote a regular user to <strong>authorized_user</strong> so they can write contractor reviews.
                        Admins can always review contractors.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: 440 }}>
                        <div>
                            <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Username</label>
                            <input
                                className="input"
                                value={promoteUsername}
                                onChange={e => setPromoteUsername(e.target.value)}
                                placeholder="Enter exact username…"
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>New Role</label>
                            <select className="input" value={promoteRole} onChange={e => setPromoteRole(e.target.value)}>
                                <option value="authorized_user">authorized_user (can write reviews)</option>
                                <option value="user">user (standard)</option>
                                <option value="admin">admin</option>
                            </select>
                        </div>
                        {promoteResult && (
                            <div style={{
                                padding: '8px 12px', borderRadius: '8px', fontSize: '13px',
                                background: promoteResult.ok ? 'var(--green-bg)' : 'var(--red-bg)',
                                color: promoteResult.ok ? 'var(--green)' : 'var(--red)',
                                border: `1px solid ${promoteResult.ok ? '#bbf7d0' : '#fecaca'}`,
                            }}>{promoteResult.text}</div>
                        )}
                        <button
                            className="btn btn-primary"
                            style={{ alignSelf: 'flex-start' }}
                            onClick={handlePromote}
                            disabled={promoting || !promoteUsername.trim()}
                        >
                            {promoting ? 'Updating…' : 'Apply Role'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
