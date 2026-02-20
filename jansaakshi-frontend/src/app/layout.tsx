import './globals.css';
import { AppProvider } from '@/context/AppContext';
import Navigation from '@/components/Navigation';
import type { Metadata } from 'next';
import 'leaflet/dist/leaflet.css';

export const metadata: Metadata = {
    title: 'JanSaakshi — Municipal Accountability',
    description: 'Track municipal projects, monitor delays, and hold government accountable.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <head>
                <link rel="manifest" href="/manifest.json" />
                <meta name="theme-color" content="#1d4ed8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
            </head>
            <body>
                <AppProvider>
                    <Navigation />
                    <main className="page-container" style={{paddingTop:150}}>{children}</main>
                </AppProvider>
            </body>
        </html>
    );
}
