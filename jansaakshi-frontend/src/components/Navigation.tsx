'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useApp } from '@/context/AppContext';
import { ReactElement } from 'react';

const icon = (d: ReactElement): ReactElement => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {d}
    </svg>
);

const icons = {
    home: icon(<><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" /><polyline points="9 22 9 12 15 12 15 22" /></>),
    projects: icon(<><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></>),
    search: icon(<><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>),
    meetings: icon(<><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></>),
    complaint: icon(<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />),
    profile: icon(<><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>),
    building: icon(<><rect x="4" y="2" width="16" height="20" rx="1" /><path d="M9 22v-4h6v4" /><path d="M8 6h.01M16 6h.01M12 6h.01M8 10h.01M16 10h.01M12 10h.01M8 14h.01M16 14h.01M12 14h.01" /></>),
    shield: icon(<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />),
    map: icon(<><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" /><line x1="8" y1="2" x2="8" y2="18" /><line x1="16" y1="6" x2="16" y2="22" /></>),
};

interface NavItem {
    href: string;
    label: string;
    icon: ReactElement;
}

const mainNav: NavItem[] = [
    { href: '/', label: 'Home', icon: icons.home },
    { href: '/projects', label: 'Projects', icon: icons.projects },
    { href: '/meetings', label: 'Meetings', icon: icons.meetings },
    { href: '/complaints', label: 'Complaints', icon: icons.complaint },
    { href: '/profile', label: 'Account', icon: icons.profile },
];

export default function Navigation() {
    const pathname = usePathname();
    const { user, city, setCity, isAdmin } = useApp();

    return (
        <>
            {/* Desktop Navbar */}
            <header className="navbar">
                <div className="navbar-inner">
                    <Link href="/" className="navbar-logo">
                        {icons.building}
                        JanSaakshi
                    </Link>

                    <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <ul className="navbar-links">
                            {mainNav.map((item) => (
                                <li key={item.href}>
                                    <Link href={item.href} className={pathname === item.href ? 'active' : ''}>
                                        {item.icon}
                                        {item.label}
                                    </Link>
                                </li>
                            ))}
                            {isAdmin && (
                                <li>
                                    <Link href="/admin" className={pathname === '/admin' ? 'active' : ''}>
                                        {icons.shield}
                                        Admin
                                    </Link>
                                </li>
                            )}
                        </ul>

                        {/* City Selector */}
                        <select
                            className="input"
                            value={city}
                            onChange={(e) => setCity(e.target.value)}
                            style={{
                                width: 'auto', padding: '6px 10px', fontSize: '13px',
                                borderRadius: '6px', marginLeft: '4px',
                            }}
                        >
                            <option value="mumbai">Mumbai</option>
                            <option value="delhi">Delhi</option>
                        </select>

                        {/* User indicator */}
                        <Link
                            href="/profile"
                            style={{
                                display: 'flex', alignItems: 'center', gap: '5px',
                                padding: '6px 10px', borderRadius: '6px', fontSize: '13px',
                                fontWeight: 500, textDecoration: 'none',
                                background: user ? 'var(--primary-light)' : 'transparent',
                                color: user ? 'var(--primary)' : 'var(--text-muted)',
                                border: user ? 'none' : '1px solid var(--border)',
                            }}
                        >
                            {icons.profile}
                            <span className="nav-user-label">{user ? user.display_name : 'Login'}</span>
                        </Link>
                    </nav>
                </div>
            </header>

            {/* Mobile Bottom Nav */}
            <nav className="bottom-nav">
                <div className="bottom-nav-inner">
                    {mainNav.map((item) => (
                        <Link key={item.href} href={item.href} className={pathname === item.href ? 'active' : ''}>
                            {item.icon}
                            <span>{item.label}</span>
                        </Link>
                    ))}
                </div>
            </nav>
        </>
    );
}

export { icons };
