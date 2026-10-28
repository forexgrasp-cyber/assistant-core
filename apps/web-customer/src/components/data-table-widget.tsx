/**
 * Data Table Widget Component
 */

'use client';

import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import type { WidgetType } from '@/types';

interface DataTableWidgetProps {
  title: string;
  data: Record<string, any>[];
  columns?: ColumnConfig[];
  pageSize?: number;
  sortable?: boolean;
  filterable?: boolean;
  exportable?: boolean;
  onRowClick?: (row: Record<string, any>) => void;
}

interface ColumnConfig {
  key: string;
  label: string;
  format?: 'currency' | 'number' | 'percent' | 'date' | 'datetime' | 'auto';
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export function DataTableWidget({ 
  title, 
  data, 
  columns, 
  pageSize = 25, 
  sortable = true, 
  filterable = true, 
  exportable = true,
  onRowClick 
}: DataTableWidgetProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});

  // Auto-generate columns from data if not provided
  const resolvedColumns = useMemo<ColumnConfig[]>(() => {
    if (columns) return columns;
    if (!data.length) return [];
    return Object.keys(data[0]).map(key => ({
      key,
      label: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      format: 'auto' as const,
      sortable: true,
    }));
  }, [columns, data]);

  // Filter data
  const filteredData = useMemo(() => {
    return data.filter(row => {
      return Object.entries(filters).every(([key, value]) => {
        if (!value) return true;
        const cellValue = String(row[key] || '').toLowerCase();
        return cellValue.includes(value.toLowerCase());
      });
    });
  }, [data, filters]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      if (aVal === bVal) return 0;
      const comparison = aVal < bVal ? -1 : 1;
      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });
  }, [filteredData, sortConfig]);

  // Pagination
  const totalPages = Math.ceil(sortedData.length / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  const handleSort = (key: string) => {
    if (!sortable) return;
    setSortConfig(current => ({
      key,
      direction: current?.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleExport = (format: 'csv' | 'json') => {
    const exportData = sortedData; // Export all sorted data
    if (format === 'csv') {
      const headers = resolvedColumns.map(c => c.label).join(',');
      const rows = exportData.map(row => 
        resolvedColumns.map(c => {
          const val = row[c.key];
          return typeof val === 'string' && val.includes(',') ? `"${val}"` : val;
        }).join(',')
      );
      const csv = [headers, ...rows].join('\n');
      downloadFile(csv, `${title.toLowerCase().replace(/\s+/g, '_')}.csv`, 'text/csv');
    } else {
      const json = JSON.stringify(exportData, null, 2);
      downloadFile(json, `${title.toLowerCase().replace(/\s+/g, '_')}.json`, 'application/json');
    }
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatCell = (value: any, format?: string) => {
    if (value === null || value === undefined) return '-';
    try {
      switch (format) {
        case 'currency':
          return typeof value === 'number' ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : value;
        case 'number':
          return typeof value === 'number' ? value.toLocaleString() : value;
        case 'percent':
          return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : value;
        case 'date':
          return value instanceof Date ? value.toLocaleDateString() : new Date(value).toLocaleDateString();
        case 'datetime':
          return value instanceof Date ? value.toLocaleString() : new Date(value).toLocaleString();
        default:
          return String(value);
      }
    } catch {
      return String(value);
    }
  };

  if (!data.length) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center py-12 text-muted-foreground">
          No data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="text-lg font-semibold">{title}</h3>
        <div className="flex items-center gap-2">
          {filterable && (
            <div className="relative">
              <input
                type="text"
                placeholder="Filter..."
                className="px-3 py-1.5 border border-input rounded-lg bg-background text-sm w-64 focus:ring-2 focus:ring-primary"
                onChange={(e) => setFilters({ ...filters, _global: e.target.value })}
              />
            </div>
          )}
          {exportable && (
            <div className="flex items-center gap-1">
              <button onClick={() => handleExport('csv')} className="px-3 py-1.5 border border-input rounded-lg hover:bg-accent text-sm flex items-center gap-1" title="Export CSV">
                <Download className="w-4 h-4" />
                <span>CSV</span>
              </button>
              <button onClick={() => handleExport('json')} className="px-3 py-1.5 border border-input rounded-lg hover:bg-accent text-sm flex items-center gap-1" title="Export JSON">
                <Download className="w-4 h-4" />
                <span>JSON</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Filters Row */}
      {filterable && resolvedColumns.some(c => c.key !== '_global') && (
        <div className="px-4 py-2 border-b border-border grid grid-cols-{Math.min(resolvedColumns.length, 6)} gap-2">
          {resolvedColumns.map(col => (
            <input
              key={col.key}
              type="text"
              placeholder={`Filter ${col.label}...`}
              className="px-2 py-1 border border-input rounded text-xs"
              value={filters[col.key] || ''}
              onChange={(e) => setFilters({ ...filters, [col.key]: e.target.value })}
            />
          ))}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-muted/50">
              {resolvedColumns.map(col => (
                <th
                  key={col.key}
                  className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:bg-accent cursor-pointer select-none"
                  style={{ width: col.width, textAlign: col.align }}
                  onClick={() => sortable && handleSort(col.key)}
                >
                  <div className="flex items-center gap-1">
                    <span>{col.label}</span>
                    {sortable && (
                      <span>
                        {sortConfig?.key === col.key ? (
                          sortConfig.direction === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                        ) : (
                          <span className="text-muted-foreground/50">⇅</span>
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {paginatedData.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="hover:bg-accent/50 transition-colors"
                onClick={() => onRowClick?.(row)}
                style={{ cursor: onRowClick ? 'pointer' : 'default' }}
              >
                {resolvedColumns.map(col => (
                  <td
                    key={col.key}
                    className="px-3 py-2 text-sm"
                    style={{ textAlign: col.align || 'left' }}
                  >
                    {formatCell(row[col.key], col.format)}
                  </td>
                ))}
              </tr>
            ))}
            {paginatedData.length === 0 && (
              <tr>
                <td colSpan={resolvedColumns.length} className="px-3 py-8 text-center text-muted-foreground">
                  No matching records
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-border flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              className="p-1.5 border border-input rounded hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 border border-input rounded hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-8 h-8 rounded font-medium text-sm transition-colors ${
                    currentPage === pageNum
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 border border-input rounded hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              className="p-1.5 border border-input rounded hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}