'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import Link from 'next/link';
import { MapContainer, TileLayer, GeoJSON, ZoomControl } from 'react-leaflet';
import type { Feature, FeatureCollection, GeoJsonObject, GeoJsonProperties } from 'geojson';
import L from 'leaflet';
import { useRouter } from "next/navigation";

type WardStat = {
    wardNumber: number;
    wardName: string;
    corporatorName: string;
    total: number;
    active: number;
    completed: number;
    delayed: number;
    stalled: number;
    total_budget: number;
    avg_delay_days: number;
};

type StatsIndex = Record<number, WardStat>;

import { API_BASE } from '@/lib/config';

export default function WardMap() {

    const [geojson, setGeojson] = useState<FeatureCollection | null>(null);
    const [stats, setStats] = useState<StatsIndex>({});
    const [selected, setSelected] = useState<number | null>(null);
    const [query, setQuery] = useState('');
    const mapRef = useRef<L.Map | null>(null);
    const geoRef = useRef<L.GeoJSON | null>(null);
    const popupRef = useRef<L.Popup | null>(null);
    const router = useRouter();

    // ---------------- LOAD DATA ----------------
    useEffect(() => {
        const load = async () => {
            const [gRes, sRes] = await Promise.all([
                fetch(`${API_BASE}/api/wards/geojson`),
                fetch(`${API_BASE}/api/wards/stats`)
            ]);

            if (!gRes.ok) throw new Error('GeoJSON failed');

            const g = (await gRes.json()) as FeatureCollection;
            const s = (await sRes.json()) as WardStat[];

            const index: StatsIndex = {};
            for (const w of s) index[w.wardNumber] = w;

            setGeojson(g);
            setStats(index);
        };

        load().catch(console.error);
    }, []);

    // ---------------- FORCE LEAFLET RESIZE ----------------
    useEffect(() => {
        if (!mapRef.current) return;

        const t = setTimeout(() => {
            mapRef.current?.invalidateSize();
        }, 600);

        return () => clearTimeout(t);
    }, [geojson]);

    useEffect(() => {

        const handler = (e: any) => {
            const ward = e.detail;
            console.log("Ward clicked:", ward);

            // 👇 later we will route here
            // router.push(`/wards/${ward}`)
        };

        window.addEventListener("ward-click", handler);

        return () => {
            window.removeEventListener("ward-click", handler);
        };

    }, []);

    useEffect(() => {

        const handleWardClick = (e: any) => {

            const wardNumber = e.detail;

            router.push(`/projects?ward=${wardNumber}`);
            // OR if you have dynamic route:
            // router.push(`/wards/${wardNumber}`)
        };

        window.addEventListener("ward-click", handleWardClick);

        return () => {
            window.removeEventListener("ward-click", handleWardClick);
        };

    }, []);

    // ---------------- STYLE ----------------
    const styleFn = useCallback((feature: Feature) => {
        const props = feature.properties as GeoJsonProperties;
        const wardNumber = Number((props as any)?.wardNumber);

        return {
            fillColor: "transparent",
            fillOpacity: 0,
            color: "#64748b",
            weight: selected === wardNumber ? 3 : 1.2,
        } as L.PathOptions;

    }, [selected]);

    // ---------------- FEATURE ----------------
    const onEachFeature = useCallback((feature: Feature, layer: L.Layer) => {

        const props = feature.properties as any;
        const wardNumber = Number(props?.wardNumber);
        const wardName = props?.wardName || `Ward ${wardNumber}`;

        // ✅ THIS SHOWS WARD NUMBER AT CENTER
        (layer as L.Path).bindTooltip(`${wardNumber}`, {
            permanent: true,
            direction: "center",
            className: "ward-number-clean",
            opacity: 1
        });

        layer.on({
            click: (e: L.LeafletMouseEvent) => {

                const map = mapRef.current;
                if (!map) return;

                setSelected(wardNumber);

                const target = e.target as L.Polygon;

                if (target.getBounds) {
                    map.fitBounds(target.getBounds(), {
                        animate: true,
                        duration: 0.5,
                        padding: [40, 40]
                    });
                }

                const st = stats[wardNumber];

                // ── Build rich popup with real stats ──────────────────
                const total = st?.total ?? 0;
                const completed = st?.completed ?? 0;
                const delayed = st?.delayed ?? 0;
                const active = st?.active ?? 0;
                const stalled = st?.stalled ?? 0;
                const budget = st?.total_budget ?? 0;
                const avgDelay = st?.avg_delay_days ?? 0;
                const corp = st?.corporatorName ?? '';
                const compPct = total > 0 ? Math.round((completed / total) * 100) : 0;
                const delPct = total > 0 ? Math.round((delayed / total) * 100) : 0;
                const budgetStr = budget >= 10_000_000
                    ? `₹${(budget / 10_000_000).toFixed(1)} Cr`
                    : budget > 0 ? `₹${(budget / 100_000).toFixed(1)} L` : '';
                const compBar = total > 0 ? (completed / total) * 100 : 0;
                const actBar = total > 0 ? (active / total) * 100 : 0;
                const delBar = total > 0 ? (delayed / total) * 100 : 0;
                const stalBar = total > 0 ? (stalled / total) * 100 : 0;

                const popupHTML = `
                <div style="min-width:210px;font-family:system-ui,sans-serif;font-size:13px;color:#1e293b">

                    <div style="font-weight:700;font-size:15px">Ward ${wardNumber}</div>
                    <div style="font-size:11px;color:#6b7280;margin-bottom:${corp ? 2 : 8}px">${wardName}</div>
                    ${corp ? `<div style="font-size:10px;color:#94a3b8;margin-bottom:8px">🏛 ${corp}</div>` : ''}

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px">
                        <div style="background:#f1f5f9;border-radius:7px;padding:7px 9px;text-align:center">
                            <div style="font-size:17px;font-weight:800;color:#1d4ed8">${total}</div>
                            <div style="font-size:9px;color:#94a3b8">Total</div>
                        </div>
                        <div style="background:#fef2f2;border-radius:7px;padding:7px 9px;text-align:center">
                            <div style="font-size:17px;font-weight:800;color:#dc2626">${delayed}</div>
                            <div style="font-size:9px;color:#94a3b8">Delayed</div>
                        </div>
                        <div style="background:#f0fdf4;border-radius:7px;padding:7px 9px;text-align:center">
                            <div style="font-size:17px;font-weight:800;color:#16a34a">${completed}</div>
                            <div style="font-size:9px;color:#94a3b8">Completed</div>
                        </div>
                        <div style="background:#fffbeb;border-radius:7px;padding:7px 9px;text-align:center">
                            <div style="font-size:17px;font-weight:800;color:#d97706">${active}</div>
                            <div style="font-size:9px;color:#94a3b8">In Progress</div>
                        </div>
                    </div>

                    ${total > 0 ? `
                    <div style="margin-bottom:8px">
                        <div style="display:flex;height:5px;border-radius:4px;overflow:hidden;background:#e2e8f0">
                            <div style="width:${compBar}%;background:#22c55e"></div>
                            <div style="width:${actBar}%;background:#f59e0b"></div>
                            <div style="width:${delBar}%;background:#ef4444"></div>
                            <div style="width:${stalBar}%;background:#a855f7"></div>
                        </div>
                        <div style="display:flex;gap:8px;margin-top:4px;font-size:9px;color:#64748b">
                            ${completed > 0 ? `<span>🟢 ${compPct}%</span>` : ''}
                            ${delayed > 0 ? `<span>🔴 ${delPct}% delayed</span>` : ''}
                            ${stalled > 0 ? `<span>🟣 ${stalled} stalled</span>` : ''}
                        </div>
                    </div>` : ''}

                    ${budgetStr || avgDelay > 0 ? `
                    <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap">
                        ${budgetStr ? `<span style="font-size:10px;background:#f1f5f9;padding:3px 7px;border-radius:5px;color:#64748b">💰 ${budgetStr}</span>` : ''}
                        ${avgDelay > 0 ? `<span style="font-size:10px;background:#fef2f2;padding:3px 7px;border-radius:5px;color:#dc2626">⏱ ${Math.round(avgDelay)}d avg delay</span>` : ''}
                    </div>` : ''}

                    <button
                        onclick="window.dispatchEvent(new CustomEvent('ward-click',{detail:${wardNumber}}))"
                        style="width:100%;padding:7px;border:none;background:#4f46e5;color:white;border-radius:7px;cursor:pointer;font-size:12px;font-weight:600"
                    >View Projects →</button>
                </div>
            `;

                if (popupRef.current) {
                    popupRef.current.remove();
                }

                popupRef.current = L.popup({
                    closeButton: true,
                    autoClose: true,
                    closeOnClick: true,
                    offset: L.point(0, -10),
                    className: "ward-popup"
                })
                    .setLatLng(e.latlng)
                    .setContent(popupHTML)
                    .openOn(map);

            }
        });

    }, [stats]);

    // ---------------- SEARCH ----------------
    const handleSearch = () => {
        const num = Number(query);
        if (!geoRef.current || Number.isNaN(num)) return;

        geoRef.current.eachLayer((l: any) => {
            const wn = Number(l.feature?.properties?.wardNumber);
            if (wn === num && mapRef.current) {
                mapRef.current.fitBounds(l.getBounds(), {
                    animate: true,
                    padding: [20, 20]
                });
            }
        });
    };

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <MapContainer
                whenReady={(e) => {
                    mapRef.current = e.target;
                    setTimeout(() => {
                        e.target.invalidateSize();
                    }, 600);
                }}
                style={{ width: '100%', height: '100%' }}
                zoom={10}
                minZoom={13}
                maxZoom={20}
                center={[19.076, 72.8777]}
                zoomControl={false}
                preferCanvas
            >
                <TileLayer
                    attribution=""
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />

                {geojson && (
                    <GeoJSON
                        ref={geoRef}
                        data={geojson as GeoJsonObject}
                        style={styleFn}
                        onEachFeature={onEachFeature}
                    />
                )}

                <ZoomControl position="bottomright" />
            </MapContainer>

            <style>{`
                .ward-number-clean {
                    background: none !important;
                    border: none !important;
                    box-shadow: none !important;
                    font-weight: 800 !important;
                    font-size: 11px !important;
                    color: #4b5563 !important;
                    text-shadow: 0 0 2px #fff !important;
                    pointer-events: none !important;
                }
                .ward-number-clean::before {
                    display: none !important;
                }
            `}</style>
        </div>
    );
}