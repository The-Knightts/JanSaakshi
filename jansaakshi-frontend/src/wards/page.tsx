import dynamic from 'next/dynamic';

const WardMap = dynamic(() => import('../components/WardMap'), { ssr: false });

export default function Page() {
  return (
    <div className="px-4 py-6">
      <h1 className="text-2xl font-semibold mb-4">Mumbai Ward Map</h1>
      <WardMap />
    </div>
  );
}

