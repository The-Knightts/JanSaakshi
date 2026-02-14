import Link from 'next/link';

export default function Home() {
  return (
    <main className="p-6">
      <h1 className="text-3xl font-bold">JanSaakshi</h1>
      <p className="mt-2 text-gray-600">Making municipal governance transparent.</p>
      <div className="mt-6">
        <Link
          href="/wards"
          className="inline-flex items-center px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 transition"
        >
          Open Mumbai Ward Map
        </Link>
      </div>
    </main>
  );
}

