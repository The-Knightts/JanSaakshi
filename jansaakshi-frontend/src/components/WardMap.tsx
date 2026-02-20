'use client';

import { useEffect, useRef, useState } from 'react';
import type L from 'leaflet';

interface CityConfig {
    lat: number;
    lng: number;
    zoom: number;
    geojson: string;
}

const CITY_CONFIG: Record<string, CityConfig> = {
    mumbai: { lat: 19.076, lng: 72.8777, zoom: 11, geojson: '/geojson/mumbai_wards.geojson' },
    delhi: { lat: 28.6139, lng: 77.209, zoom: 11, geojson: '/geojson/delhi_wards.geojson' },
};

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

interface WardMapProps {
    city?: string;
    onWardClick?: (wardNo: string, wardName: string) => void;
}

export default function WardMap({ city = 'mumbai', onWardClick }: WardMapProps) {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstance = useRef<L.Map | null>(null);
    const layerRef = useRef<L.GeoJSON | null>(null);
    const [leaflet, setLeaflet] = useState<typeof L | null>(null);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        import('leaflet').then((m) => {
            setLeaflet(m.default || m);
            import('leaflet/dist/leaflet.css');
        });
    }, []);

    useEffect(() => {
        if (!leaflet || !mapRef.current) return;
        const cfg = CITY_CONFIG[city] || CITY_CONFIG.mumbai;

        if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; }

        const map = leaflet.map(mapRef.current).setView([cfg.lat, cfg.lng], cfg.zoom);
        leaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap', maxZoom: 18,
        }).addTo(map);
        mapInstance.current = map;
        loadWards(map, cfg);

        return () => { if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; } };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [leaflet, city]);

    const loadWards = async (map: L.Map, cfg: CityConfig) => {
        if (!leaflet) return;
        try {
            const geoRes = await fetch(cfg.geojson);
            const geoData = await geoRes.json();

            const stats: Record<string, any> = {};
            try {
                const sRes = await fetch(`${API}/api/wards?city=${city}`);
                const wardStats = await sRes.json();
                if (Array.isArray(wardStats)) wardStats.forEach((w: any) => { stats[w.ward_no] = w; });
            } catch { }

            if (layerRef.current) map.removeLayer(layerRef.current);

            layerRef.current = leaflet.geoJSON(geoData, {
                pointToLayer: (f: any, latlng: L.LatLng) => {
                    const wn = f.properties.ward_no || f.properties.ward_number || f.properties.WARD_NO;
                    const s = stats[wn] || {};
                    const d = s.delayed_projects || 0;
                    const color = d === 0 ? '#16a34a' : d <= 2 ? '#d97706' : '#dc2626';
                    return leaflet.circleMarker(latlng, {
                        radius: 14, fillColor: color, fillOpacity: 0.6,
                        stroke: true, weight: 2, color: '#fff',
                    });
                },
                onEachFeature: (f: any, layer: L.Layer) => {
                    const wn = f.properties.ward_no || f.properties.ward_number || f.properties.WARD_NO;
                    const wname = f.properties.ward_name || '';
                    const wzone = f.properties.ward_zone || '';
                    const s = stats[wn] || {};

                    (layer as any).bindPopup(`
            <div style="font-family:Inter,sans-serif;min-width:150px">
              <h3 style="margin:0 0 2px;font-size:15px;font-weight:600">Ward ${wn}</h3>
              <p style="margin:0 0 6px;color:#64748b;font-size:13px">${wname}${wzone ? ` (${wzone})` : ''}</p>
              <div style="font-size:13px">
                <div>Projects: <b>${s.total_projects || 0}</b></div>
                <div>Delayed: <b style="color:#dc2626">${s.delayed_projects || 0}</b></div>
                <div>Completed: <b style="color:#16a34a">${s.completed_projects || 0}</b></div>
                ${s.ward_zone ? `<div>Zone: <b>${s.ward_zone}</b></div>` : ''}
              </div>
            </div>
          `);

                    (layer as any).bindTooltip(wzone || wn, { permanent: true, direction: 'center', className: 'ward-label' });
                    layer.on('click', () => onWardClick?.(wn, wname));
                    layer.on('mouseover', () => (layer as any).setStyle({ fillOpacity: 1, weight: 3 }));
                    layer.on('mouseout', () => (layer as any).setStyle({ fillOpacity: 0.6, weight: 2 }));
                },
            }).addTo(map);
        } catch (e) { console.error('Map load error:', e); }
    };

    return (
        <div style={{ position: 'relative' }}>
            <div ref={mapRef} style={{ height: '500px', width: '100%' }} />
            <div style={{
                position: 'absolute', bottom: 12, right: 12, background: 'rgba(255,255,255,.95)',
                padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', zIndex: 1000,
                boxShadow: 'var(--shadow)',
            }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '.3px' }}>Status</div>
                {[{ c: '#16a34a', l: 'No Delays' }, { c: '#d97706', l: '1-2 Delays' }, { c: '#dc2626', l: '3+ Delays' }].map(i => (
                    <div key={i.l} style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2 }}>
                        <div style={{ width: 9, height: 9, borderRadius: '50%', background: i.c }} />
                        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{i.l}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
