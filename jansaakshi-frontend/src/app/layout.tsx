import './globals.css';
import { AppProvider } from '@/context/AppContext';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import type { Metadata } from 'next';
import 'leaflet/dist/leaflet.css';
import { Outfit, Noto_Sans_Devanagari } from 'next/font/google';

const outfit = Outfit({
    subsets: ['latin'],
    variable: '--font-outfit',
});

const notoDevenagari = Noto_Sans_Devanagari({
    subsets: ['devanagari'],
    variable: '--font-noto-devenagari',
    weight: ['400', '500', '600', '700', '900'],
});

export const metadata: Metadata = {
    title: 'JanSaakshi — Municipal Accountability',
    description: 'Track municipal projects, monitor delays, and hold government accountable.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${outfit.variable} ${notoDevenagari.variable}`}>
            <head>
                <link rel="manifest" href="/manifest.json" />
                <meta name="theme-color" content="#1d4ed8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
            </head>
            <body className="flex flex-col min-h-screen">
                <AppProvider>
                    <Navigation />
                    <main className="page-container flex-grow" style={{paddingTop:120}}>{children}</main>
                    <Footer />
                </AppProvider>
            </body>
        </html>
    );
}
