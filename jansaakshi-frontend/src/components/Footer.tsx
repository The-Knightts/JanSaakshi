"use client";

import Link from "next/link";
import { Building2, Github, Twitter, Mail, ExternalLink, ShieldCheck, Heart } from "lucide-react";

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="footer-premium">
            <div className="footer-content">
                <div className="footer-grid">

                    {/* Brand Column */}
                    <div className="footer-brand">
                        <Link href="/" className="footer-logo">
                            <Building2 size={24} className="text-blue-500" />
                            <span>JanSaakshi</span>
                        </Link>
                        <p className="footer-tagline">
                            Empowering citizens through radical transparency. Track, report, and build the future of our urban landscape.
                        </p>
                        <div className="footer-socials">
                            <a href="#" className="social-link"><Twitter size={18} /></a>
                            <a href="#" className="social-link"><Github size={18} /></a>
                            <a href="#" className="social-link"><Mail size={18} /></a>
                        </div>
                    </div>

                    {/* Platform Links */}
                    <div className="footer-links-col">
                        <h4 className="footer-heading">Platform</h4>
                        <ul className="footer-links">
                            <li><Link href="/">Dashboards</Link></li>
                            <li><Link href="/projects">Infrastructure Projects</Link></li>
                            <li><Link href="/contractors">Contractor Directory</Link></li>
                            <li><Link href="/map">Live Action Map</Link></li>
                        </ul>
                    </div>

                    {/* Civic Action Links */}
                    <div className="footer-links-col">
                        <h4 className="footer-heading">Civic Action</h4>
                        <ul className="footer-links">
                            <li><Link href="/complaints">File Grievance</Link></li>
                            <li><Link href="/meetings">Town Hall Meetings</Link></li>
                            <li><Link href="/profile">My Neighborhood</Link></li>
                            <li><a href="#" className="flex items-center gap-1">Open Data API <ExternalLink size={12} /></a></li>
                        </ul>
                    </div>

                    {/* Support Column */}
                    <div className="footer-links-col">
                        <h4 className="footer-heading">Resources</h4>
                        <ul className="footer-links">
                            <li><Link href="#">How it Works</Link></li>
                            <li><Link href="#">Safety Guidelines</Link></li>
                            <li><Link href="#">Privacy Charter</Link></li>
                            <li><Link href="#">Accessibility</Link></li>
                        </ul>
                    </div>

                </div>

                <div className="footer-bottom">
                    <div className="footer-bottom-inner">
                        <p className="footer-copyright">
                            © {currentYear} JanSaakshi. All municipal data is sourced from public records.
                        </p>

                        <div className="footer-meta">
                            <div className="flex items-center gap-2 text-slate-400">
                                <ShieldCheck size={14} className="text-emerald-500" />
                                <span>Verified Data Engine</span>
                            </div>
                            <span className="footer-separator">•</span>
                            <div className="flex items-center gap-2 text-slate-400">
                                <Heart size={14} className="text-rose-500 fill-rose-500" />
                                <span>Made for Mumbai</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </footer>
    );
}
