import 'server-only';

type Props = { params: { wardNumber: string } };

type WardDetail = {
  wardNumber: number;
  wardName: string;
  corporatorName: string;
  total: number;
  active: number;
  completed: number;
  delayed: number;
};



export default async function WardDashboard({ params }: Props) {
  const base = process.env.API_BASE_URL || 'http://localhost:4000';

  let data: WardDetail | null = null;

  try {
    const res = await fetch(
      `${base}/api/wards/${params.wardNumber}`,
      { cache: 'no-store' }
    );

    if (res.ok) {
      data = await res.json();
    }
  } catch (error) {
    console.error("Failed to fetch ward data:", error);
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">
          Ward {params.wardNumber} Dashboard
        </h1>

        {!data ? (
          <div className="bg-white p-6 rounded-lg shadow text-gray-600">
            Data not available
          </div>
        ) : (
          <>
            {/* Ward Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="p-5 rounded-xl bg-white shadow">
                <div className="text-sm text-gray-500">Ward Name</div>
                <div className="text-xl font-semibold">
                  {data.wardName || `Ward ${params.wardNumber}`}
                </div>
              </div>

              <div className="p-5 rounded-xl bg-white shadow">
                <div className="text-sm text-gray-500">Corporator</div>
                <div className="text-xl font-semibold">
                  {data.corporatorName || "Not Assigned"}
                </div>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <StatCard title="Total Projects" value={data.total} />
              <StatCard title="Active" value={data.active} color="text-green-600" />
              <StatCard title="Completed" value={data.completed} color="text-blue-600" />
              <StatCard title="Delayed" value={data.delayed} color="text-red-600" />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  color = "text-gray-800"
}: {
  title: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="p-6 rounded-xl bg-white shadow">
      <div className="text-sm text-gray-500">{title}</div>
      <div className={`text-2xl font-bold ${color}`}>
        {value ?? 0}
      </div>
    </div>
  );
}
