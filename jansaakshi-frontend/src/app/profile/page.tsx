'use client';

import { useState } from 'react';
import { useApp } from '@/context/AppContext';

export default function ProfilePage() {
    const { user, login, signup, logout, city, setCity } = useApp();
    const [mode, setMode] = useState('login');
    const [form, setForm] = useState({ username: '', password: '', display_name: '', city: 'mumbai', ward: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [signupSuccess, setSignupSuccess] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        if (mode === 'login') {
            const result = await login(form.username, form.password);
            if (!result.success) setError(result.error || 'Invalid credentials');
        } else {
            const result = await signup(form);
            if (result.success) {
                setSignupSuccess(true);
            } else {
                setError(result.error || 'Something went wrong');
            }
        }
        setLoading(false);
    };

    if (user) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '500px' }}>
                <div>
                    <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>Account</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Manage your preferences</p>
                </div>

                {signupSuccess && (
                    <div style={{
                        padding: '10px 16px', borderRadius: '8px', fontSize: '14px',
                        background: 'var(--green-bg, #f0fdf4)', color: 'var(--green, #16a34a)',
                        border: '1px solid #bbf7d0', fontWeight: 500,
                    }}>
                        🎉 Account created successfully! Welcome, {user.display_name}.
                    </div>
                )}
                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <div>
                            <h2 style={{ fontSize: '18px', fontWeight: 600 }}>{user.display_name}</h2>
                            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>@{user.username} · {user.role}</p>
                        </div>
                        <button className="btn btn-outline" onClick={logout} style={{ fontSize: '13px' }}>Log Out</button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div>
                            <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>City</label>
                            <select className="input" value={city} onChange={(e) => setCity(e.target.value)}>
                                <option value="mumbai">Mumbai</option>
                                <option value="delhi">Delhi</option>
                            </select>
                        </div>
                        <div>
                            <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Ward Number</label>
                            <input className="input" value={user.ward || ''} disabled style={{ background: 'var(--bg)' }} />
                            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Ward is set during signup</p>
                        </div>
                    </div>
                </div>

                <div className="card">
                    <h2 className="card-title" style={{ marginBottom: '8px' }}>About JanSaakshi</h2>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        A civic accountability platform making municipal project data accessible. Upload meeting minutes, search projects, track delays, and raise complaints. Built for transparency.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '400px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center' }}>
                <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>
                    {mode === 'login' ? 'Log In' : 'Create Account'}
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                    {mode === 'login' ? 'Access personalized ward updates' : 'Sign up to follow projects and raise complaints'}
                </p>
            </div>

            <form onSubmit={handleSubmit} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {error && (
                    <div style={{ padding: '8px 12px', borderRadius: '6px', background: 'var(--red-bg)', color: 'var(--red)', fontSize: '13px' }}>
                        {error}
                    </div>
                )}

                <div>
                    <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Username</label>
                    <input className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
                </div>
                <div>
                    <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Password</label>
                    <input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
                </div>

                {mode === 'signup' && (
                    <>
                        <div>
                            <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Display Name</label>
                            <input className="input" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                            <div>
                                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>City</label>
                                <select className="input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}>
                                    <option value="mumbai">Mumbai</option>
                                    <option value="delhi">Delhi</option>
                                </select>
                            </div>
                            <div>
                                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Ward No.</label>
                                <input className="input" value={form.ward} onChange={(e) => setForm({ ...form, ward: e.target.value })} placeholder="e.g. 77" />
                            </div>
                        </div>
                    </>
                )}

                <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                    {loading ? 'Please wait...' : mode === 'login' ? 'Log In' : 'Create Account'}
                </button>

                <div style={{ textAlign: 'center' }}>
                    <button type="button" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }}
                        style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: '13px' }}>
                        {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Log in'}
                    </button>
                </div>
            </form>

            <p style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
                Login is optional. You can browse all projects without an account.
            </p>
        </div>
    );
}
