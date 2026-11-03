import Link from "next/link";

export default function Home() {
  return (
    <div className="text-center py-20">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">Developer Console</h1>
      <p className="text-gray-500 mb-8">Build schemas, design workflows, and manage vertical packs and tenants.</p>
      <div className="flex justify-center gap-3">
        <Link href="/schema" className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
          Schema Builder
        </Link>
        <Link href="/workflows" className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50">
          Workflow Designer
        </Link>
      </div>
    </div>
  );
}
