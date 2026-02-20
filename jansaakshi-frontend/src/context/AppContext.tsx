'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { API_BASE } from '@/lib/config';

const API = API_BASE;

interface AppContextValue {
    user: any;
    city: string;
    setCity: (city: string) => void;
    token: string | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
    signup: (formData: any) => Promise<{ success: boolean; error?: string }>;
    logout: () => Promise<void>;
    apiFetch: (url: string, options?: RequestInit) => Promise<Response>;
    isAdmin: boolean;
    API: string;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<any>(null);
    const [city, setCity] = useState('mumbai');
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    // Restore from localStorage
    useEffect(() => {
        const saved = localStorage.getItem('jansaakshi');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                if (parsed.token) setToken(parsed.token);
                if (parsed.city) setCity(parsed.city);
            } catch { }
        }
        setLoading(false);
    }, []);

    // Fetch user when token changes
    useEffect(() => {
        if (!token) { setUser(null); return; }
        fetch(`${API}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.user) {
                    setUser(data.user);
                    if (data.user.city_name) setCity(data.user.city_name);
                } else {
                    setToken(null);
                    setUser(null);
                }
            })
            .catch(() => { });
    }, [token]);

    // Persist
    useEffect(() => {
        localStorage.setItem('jansaakshi', JSON.stringify({ token, city }));
    }, [token, city]);

    const login = useCallback(async (username: string, password: string) => {
        const res = await fetch(`${API}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (data.success) {
            setToken(data.token);
            setUser(data.user);
            if (data.user.city_name) setCity(data.user.city_name);
            return { success: true };
        }
        return { success: false, error: data.error };
    }, []);

    const signup = useCallback(async (formData: any) => {
        const res = await fetch(`${API}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        });
        const data = await res.json();
        if (data.success) {
            setToken(data.token);
            setUser(data.user);
            return { success: true };
        }
        return { success: false, error: data.error };
    }, []);

    const logout = useCallback(async () => {
        if (token) {
            fetch(`${API}/api/auth/logout`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            }).catch(() => { });
        }
        setToken(null);
        setUser(null);
    }, [token]);

    // Helper: add auth + city headers
    const apiFetch = useCallback((url: string, options: RequestInit = {}) => {
        const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
        if (token) headers.Authorization = `Bearer ${token}`;
        headers['X-City'] = city;

        const separator = url.includes('?') ? '&' : '?';
        const fullUrl = `${API}${url}${separator}city=${city}`;
        return fetch(fullUrl, { ...options, headers });
    }, [token, city]);

    // Auto-detect location
    const detectCity = useCallback(() => {
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition((pos) => {
            const { latitude } = pos.coords;
            if (latitude >= 27 && latitude <= 30) setCity('delhi');
            else if (latitude >= 18 && latitude <= 21) setCity('mumbai');
        }, () => { });
    }, []);

    useEffect(() => {
        if (!loading && !user) detectCity();
    }, [loading, user, detectCity]);

    return (
        <AppContext.Provider value={{
            user, city, setCity, token, loading,
            login, signup, logout, apiFetch,
            isAdmin: user?.role === 'admin',
            API,
        }}>
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be within AppProvider');
    return ctx;
}
