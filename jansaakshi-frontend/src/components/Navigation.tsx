"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useApp } from "@/context/AppContext";
import CardNav from "./CardNav";
import { ReactNode } from "react";

const icon = (d: ReactNode) => (
    <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
    >
        {d}
    </svg>
);

const icons = {
    home: icon(
        <>
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" />
            <polyline points="9 22 9 12 15 12 15 22" />
        </>
    ),
    projects: icon(
        <>
            <rect x="2" y="3" width="20" height="14" rx="2" />
            <line x1="8" y1="21" x2="16" y2="21" />
            <line x1="12" y1="17" x2="12" y2="21" />
        </>
    ),
    search: icon(
        <>
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </>
    ),
    meetings: icon(
        <>
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
        </>
    ),
    complaint: icon(
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    ),
    profile: icon(
        <>
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
        </>
    ),
    building: icon(
        <>
            <rect x="4" y="2" width="16" height="20" rx="1" />
            <path d="M9 22v-4h6v4" />
            <path d="M8 6h.01M16 6h.01M12 6h.01M8 10h.01M16 10h.01M12 10h.01M8 14h.01M16 14h.01M12 14h.01" />
        </>
    ),
    shield: icon(<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />),
    map: icon(
        <>
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
            <line x1="8" y1="2" x2="8" y2="18" />
            <line x1="16" y1="6" x2="16" y2="22" />
        </>
    ),
};

const contractorIcon = icon(
    <>
        <path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        <rect x="2" y="8" width="20" height="14" rx="2" />
        <path d="M6 12h.01M10 12h.01M14 12h.01M18 12h.01M6 16h.01M10 16h.01M14 16h.01M18 16h.01" />
    </>
);

const mainNav = [
    { href: "/", label: "Home", icon: icons.home },
    { href: "/projects", label: "Projects", icon: icons.projects },
    { href: "/contractors", label: "Contractors", icon: contractorIcon },
    { href: "/meetings", label: "Meetings", icon: icons.meetings },
    { href: "/complaints", label: "Complaints", icon: icons.complaint },
    { href: "/profile", label: "Account", icon: icons.profile },
];

const cardNavItems = [
    {
        label: "Explore",
        bgColor: "#f0f7ff",
        textColor: "#0055ff",
        links: [
            { label: "Home", href: "/", ariaLabel: "Go to Home" },
            { label: "Projects", href: "/projects", ariaLabel: "View Projects" },
            { label: "Contractors", href: "/contractors", ariaLabel: "Contractor Directory" },
        ],
    },
    {
        label: "Engage",
        bgColor: "#e1efff",
        textColor: "#0044cc",
        links: [
            { label: "Meetings", href: "/meetings", ariaLabel: "View Meetings" },
            {
                label: "Complaints",
                href: "/complaints",
                ariaLabel: "File Complaints",
            },
        ],
    },
    {
        label: "Account",
        bgColor: "#d1e7ff",
        textColor: "#0033aa",
        links: [{ label: "Profile", href: "/profile", ariaLabel: "Your Profile" }],
    },
];

const LogoElement = (
    <Link
        href="/"
        className="logo-text"
        style={{ textDecoration: "none", color: "#0055ff" }}
    >
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ width: 24, height: 24 }}
        >
            <rect x="4" y="2" width="16" height="20" rx="1" />
            <path d="M9 22v-4h6v4" />
            <path d="M8 6h.01M16 6h.01M12 6h.01M8 10h.01M16 10h.01M12 10h.01M8 14h.01M16 14h.01M12 14h.01" />
        </svg>
        JanSaakshi
    </Link>
);

export default function Navigation() {
    const pathname = usePathname();
    const { isAdmin } = useApp();

    // If user is admin, add admin link to the Account card
    const items = isAdmin
        ? cardNavItems.map((item) =>
            item.label === "Account"
                ? {
                    ...item,
                    links: [
                        ...item.links,
                        { label: "Admin", href: "/admin", ariaLabel: "Admin Panel" },
                    ],
                }
                : item
        )
        : cardNavItems;

    return (
        <>
            {/* Desktop: Animated CardNav */}
            <CardNav
                logo={LogoElement}
                logoAlt="JanSaakshi"
                items={items}
                baseColor="#ffffff"
                menuColor="#0055ff"
                buttonBgColor="#0055ff"
                buttonTextColor="#ffffff"
                ease="power3.out"
            />

            {/* Mobile Bottom Nav (unchanged) */}
            <nav className="bottom-nav">
                <div className="bottom-nav-inner">
                    {mainNav.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={pathname === item.href ? "active" : ""}
                        >
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