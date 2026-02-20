'use client';

import { useState, useEffect, useCallback } from 'react';
import { useApp } from '@/context/AppContext';

export default function MeetingsPage() {
    const { user, apiFetch, city } = useApp();
    const [meetings, setMeetings] = useState([]);
    const [ward, setWard] = useState(user?.ward_number || '');
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = ward ? `?ward=${ward}` : '';
            const res = await apiFetch(`/api/meetings${params}`);
            if (res.ok) setMeetings((await res.json()).meetings || []);
        } catch { }
        setLoading(false);
    }, [ward, apiFetch]);

    useEffect(() => {
        if (user?.ward_number && !ward) setWard(user.ward_number);
    }, [user, ward]);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
                <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>Meetings</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                    Recent ward committee meetings in {city === 'delhi' ? 'Delhi' : 'Mumbai'}
                </p>
            </div>

            {/* Ward filter */}
            <div className="card" style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                    className="input"
                    placeholder="Filter by ward (e.g. R/S or Central)"
                    value={ward}
                    onChange={(e) => setWard(e.target.value)}
                    style={{ maxWidth: '300px' }}
                />
                <button className="btn btn-primary" onClick={load}>Filter</button>
                {ward && (
                    <button className="btn btn-outline" onClick={() => { setWard(''); }}>
                        Show all
                    </button>
                )}
            </div>

            {!ward && !user?.ward_number && (
                <div className="card" style={{ background: 'var(--primary-light)', borderColor: '#bfdbfe' }}>
                    <p style={{ color: 'var(--primary)', fontSize: '13px' }}>
                        Enter a ward number above to see meetings for your area, or log in to set a default ward.
                    </p>
                </div>
            )}

            <div className="card">
                <h2 className="card-title" style={{ marginBottom: '12px' }}>
                    {ward ? `Meetings — Ward ${ward}` : 'All Recent Meetings'}
                </h2>
                {loading ? (
                    <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
                ) : meetings.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No meetings found{ward ? ` for ward ${ward}` : ''}.</p>
                ) : (
                    meetings.map((m, i) => (
                        <div key={i} className="project-item" style={{ flexDirection: 'column', gap: '6px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%' }}>
                                <div>
                                    <div className="project-name">{m.meeting_type === 'ward_committee' ? 'Ward Committee Meeting' : m.meeting_type === 'zone_committee' ? 'Zone Committee Meeting' : m.meeting_type || 'Meeting'}</div>
                                    <div className="project-meta">Ward {m.ward_number} – {m.ward_name} · {m.meeting_date}</div>
                                </div>
                                {m.projects_count > 0 && (
                                    <span className="status-badge status-approved">{m.projects_count} projects</span>
                                )}
                            </div>
                            {m.objective && (
                                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{m.objective}</p>
                            )}
                            {m.venue && (
                                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Venue: {m.venue}</p>
                            )}
                            {m.attendees && (
                                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Attendees: {m.attendees}</p>
                            )}
                            {m.projects_discussed && (
                                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Projects discussed: {m.projects_discussed}</p>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
