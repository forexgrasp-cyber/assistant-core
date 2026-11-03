"use client";

import { useEffect, useState } from "react";
import { FileText, Download } from "lucide-react";

const API = "/api";

export default function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    setLoading(false);
  }, []);

  const generate = async () => {
    const res = await fetch(`${API}/reports?format=pdf`, { method: "POST" });
    const data = await res.json();
    setResult(data);
    setReports((prev) => [...prev, data]);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Reports</h1>
      <p className="text-gray-500 mb-6">Generate retention reports (PDF/HTML/CSV/JSON) from workflow and metric data.</p>

      <div className="flex gap-3 mb-8">
        <button onClick={generate} className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
          <FileText className="w-4 h-4 mr-2 inline" /> Generate Report
        </button>
      </div>

      {result && (
        <div className="bg-white p-4 rounded border border-gray-200 shadow-sm mb-6">
          <h3 className="font-semibold text-gray-900 mb-2">Last report</h3>
          <p className="text-sm text-gray-600 mb-2">{result.name ?? "Retention Report"} ({result.format})</p>
          <div className="flex gap-2">
            <a href={result.download_url} target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 text-indigo-600 hover:underline text-sm">
              <Download className="w-4 h-4 mr-1 inline" /> Download
            </a>
          </div>
        </div>
      )}

      <div className="bg-white p-5 rounded border border-gray-200 shadow-sm">
        <h3 className="font-semibold text-gray-900 mb-3">Report history</h3>
        <div className="text-sm text-gray-500">{reports.length} reports generated this session.</div>
      </div>
    </div>
  );
}
