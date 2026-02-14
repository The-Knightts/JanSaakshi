'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import Link from 'next/link';
import { MapContainer, TileLayer, GeoJSON, ZoomControl } from 'react-leaflet';
import type { Feature, FeatureCollection, GeoJsonObject, GeoJsonProperties } from 'geojson';
import L from 'leaflet';

type WardStat = {
  wardNumber: number;
  wardName: string;
  corporatorName: string;
  total: number;
  active: number;
  completed: number;
  delayed: number;
};

type StatsIndex = Record<number, WardStat>;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export default function WardMap() {
  const [geojson, setGeojson] = useState<FeatureCollection | null>(null);
  const [stats, setStats] = useState<StatsIndex>({});
  const [selected, setSelected] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [geoSource, setGeoSource] = useState<string>('');
  const [featureCount, setFeatureCount] = useState<number>(0);
  const mapRef = useRef<L.Map | null>(null);
  const geoRef = useRef<L.GeoJSON | null>(null);
  const labelLayerRef = useRef<L.LayerGroup | null>(null);


  useEffect(() => {
    const load = async () => {
      const [gRes, sRes] = await Promise.all([
        fetch(`${API_BASE}/api/wards/geojson`),
        fetch(`${API_BASE}/api/wards/stats`)
      ]);
      if (!gRes.ok) throw new Error('Failed to load GeoJSON');
      const source = gRes.headers.get('x-geojson-source') || '';
      const g = (await gRes.json()) as FeatureCollection;
      const s = (await sRes.json()) as WardStat[];
      const index: StatsIndex = {};
      for (const w of s) index[w.wardNumber] = w;
      setGeojson(g);
      setStats(index);
      setGeoSource(source);
      setFeatureCount(g.features?.length || 0);
    };
    load().catch(() => { });
  }, []);

  const getColor = (st?: WardStat) => {
    if (!st) return '#9ca3af';
    if (st.delayed > 0) return '#ef4444';
    if (st.active > 0 && st.completed > 0) return '#f59e0b';
    return '#22c55e';
  };

  const baseStyle = useMemo(() => {
    return {
      weight: 0,
      fillOpacity: 0.55,
      smoothFactor: 1
    } as L.PathOptions;
  }, []);

  const styleFn = useCallback((feature: Feature) => {
    const props = feature.properties as GeoJsonProperties;
    const wardNumber = Number(
      (props as { wardNumber?: number | string } | null)?.wardNumber
    );

    const isSelected = selected === wardNumber;

    return {
      fillColor: "#ffffff",      // white inside
      fillOpacity: 0.2,
      color: "#000000",          // black border
      weight: isSelected ? 2 : 1,
    } as L.PathOptions;

  }, [selected]);


  const onEachFeature = useCallback((feature: Feature, layer: L.Layer) => {
    const props = feature.properties as GeoJsonProperties;
    const wardNumber = Number(
      (props as { wardNumber?: number | string } | null)?.wardNumber
    );

    // Clean permanent number in center
    (layer as L.Path).bindTooltip(
      `${wardNumber}`,
      {
        permanent: true,
        direction: "center",
        className: "ward-number-clean"
      }
    );

    layer.on({
      click: (e: L.LeafletMouseEvent) => {
        setSelected(wardNumber);

        const map = mapRef.current;
        const target = e.target as L.Polygon;

        if (map && target.getBounds) {
          const bounds = target.getBounds();
          map.fitBounds(bounds, { animate: true, padding: [20, 20] });
        }
      }
    });

  }, []);




  const selectedData = useMemo(
    () => (selected != null ? stats[selected] : null),
    [selected, stats]
  );

  const handleSearch = () => {
    const num = Number(query);
    if (!geoRef.current || Number.isNaN(num)) return;
    let found: L.Layer | null = null;
    geoRef.current.eachLayer((l: L.Layer) => {
      const layer = l as L.Layer & { feature?: Feature };
      const props = layer.feature?.properties as GeoJsonProperties;
      const wn = Number((props as { wardNumber?: number | string } | null)?.wardNumber);
      if (wn === num) found = l;
    });
    if (found && mapRef.current) {
      const target = found as L.Polygon;
      if (target.getBounds) {
        setSelected(num);
        mapRef.current.fitBounds(target.getBounds(), { animate: true, padding: [20, 20] });
      }
    }
  };

  useEffect(() => {
    if (!mapRef.current) return;

    const map = mapRef.current;

    const handleZoom = () => {
      const zoom = map.getZoom();

      geoRef.current?.eachLayer((layer: any) => {
        if (layer.getTooltip) {
          if (zoom >= 12) {
            layer.getTooltip().getElement()?.classList.remove("hidden-number");
          } else {
            layer.getTooltip().getElement()?.classList.add("hidden-number");
          }
        }
      });
    };

    map.on("zoomend", handleZoom);

    handleZoom();

    return () => {
      map.off("zoomend", handleZoom);
    };
  }, []);


  return (
    <div className="relative w-full h-[80vh] md:h-[85vh]">
      <div className="absolute z-[1000] top-4 left-4 bg-white/90 backdrop-blur rounded-lg shadow p-3 flex items-center gap-2">
        <input
          className="border rounded px-3 py-2 w-40 md:w-56 text-sm"
          placeholder="Search ward number"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch();
          }}
        />
        <button
          onClick={handleSearch}
          className="px-3 py-2 rounded bg-indigo-600 text-white text-sm hover:bg-indigo-700 active:scale-[0.98] transition"
        >
          Search
        </button>
      </div>

      <div className="absolute z-[1000] bottom-4 left-4 bg-white/90 backdrop-blur rounded-lg shadow p-3 text-xs">
        <div className="font-medium mb-2">Legend</div>
        <div className="flex items-center gap-2 mb-1">
          <span className="inline-block w-3 h-3 rounded" style={{ background: '#ef4444' }} />
          <span>Delayed projects</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <span className="inline-block w-3 h-3 rounded" style={{ background: '#22c55e' }} />
          <span>On track</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded" style={{ background: '#f59e0b' }} />
          <span>Mixed status</span>
        </div>
        <div className="mt-2 text-[11px] text-gray-600">
          Source: {geoSource || 'unknown'} • Wards: {featureCount}
        </div>
      </div>

      <div className="absolute z-[1000] top-4 right-4 w-[90vw] max-w-[24rem]">
        {selectedData ? (
          <div className="bg-white/95 backdrop-blur rounded-xl shadow-lg p-4">
            <div className="text-sm text-gray-500">Ward {selectedData.wardNumber}</div>
            <div className="text-lg font-semibold">{selectedData.wardName}</div>
            <div className="mt-1 text-sm">Corporator: <span className="font-medium">{selectedData.corporatorName}</span></div>
            <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
              <div className="p-3 rounded bg-gray-50">
                <div className="text-gray-500">Total</div>
                <div className="text-lg font-semibold">{selectedData.total}</div>
              </div>
              <div className="p-3 rounded bg-emerald-50">
                <div className="text-gray-600">Active</div>
                <div className="text-lg font-semibold text-emerald-700">{selectedData.active}</div>
              </div>
              <div className="p-3 rounded bg-blue-50">
                <div className="text-gray-600">Completed</div>
                <div className="text-lg font-semibold text-blue-700">{selectedData.completed}</div>
              </div>
              <div className="p-3 rounded bg-red-50">
                <div className="text-gray-600">Delayed</div>
                <div className="text-lg font-semibold text-red-700">{selectedData.delayed}</div>
              </div>
            </div>
            <Link
              href={`/wards/${selectedData.wardNumber}`}
              className="mt-4 inline-flex items-center justify-center w-full px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 active:scale-[0.98] transition"
            >
              View Full Ward Dashboard
            </Link>
          </div>
        ) : (
          <div className="bg-white/95 backdrop-blur rounded-xl shadow-lg p-4 text-sm text-gray-600">
            Select a ward to view details
          </div>
        )}
      </div>

      <MapContainer
        whenCreated={(m) => {
          mapRef.current = m;
          labelLayerRef.current = L.layerGroup().addTo(m);
        }}
        className="w-full h-full rounded-xl overflow-hidden"
        zoom={11}
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
    </div>
  );
}

