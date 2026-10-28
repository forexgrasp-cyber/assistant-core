/**
 * Chart Widget Component using Recharts
 */

'use client';

import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ComposedChart
} from 'recharts';
import type { WidgetType } from '@/types';

interface ChartWidgetProps {
  title: string;
  type: WidgetType;
  data: Record<string, any>[];
  xKey: string;
  yKeys: string[];
  height?: number;
  colors?: string[];
  stacked?: boolean;
}

const CHART_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
];

export function ChartWidget({ title, type, data, xKey, yKeys, height = 300, colors = CHART_COLORS, stacked = false }: ChartWidgetProps) {
  if (!data.length) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 h-{height} flex items-center justify-center">
        <p className="text-muted-foreground">No data available</p>
      </div>
    );
  }

  const renderCustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload) return null;
    return (
      <div className="bg-card border border-border rounded-lg p-3 shadow-lg min-w-[150px]">
        <p className="font-medium text-sm mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />
            <span className="font-medium">{entry.name}: </span>
            <span>{formatValue(entry.value)}</span>
          </p>
        ))}
      </div>
    );
  };

  const formatValue = (value: any) => {
    if (typeof value === 'number') {
      if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
      if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
      return value.toLocaleString();
    }
    return String(value);
  };

  const renderChart = () => {
    if (type === 'line_chart') {
      return (
        <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} tickFormatter={formatValue} />
          <Tooltip content={renderCustomTooltip} />
          <Legend />
          {yKeys.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              stroke={colors[index % colors.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      );
    }

    if (type === 'area_chart') {
      return (
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} tickFormatter={formatValue} />
          <Tooltip content={renderCustomTooltip} />
          <Legend />
          {yKeys.map((key, index) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              name={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              stroke={colors[index % colors.length]}
              fill={colors[index % colors.length]}
              fillOpacity={0.2}
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      );
    }

    if (type === 'bar_chart') {
      return (
        <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }} layout={stacked ? 'vertical' : 'horizontal'}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          {stacked ? (
            <>
              <YAxis dataKey={xKey} type="category" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} width={100} />
              <XAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} tickFormatter={formatValue} />
            </>
          ) : (
            <>
              <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} tickFormatter={formatValue} />
            </>
          )}
          <Tooltip content={renderCustomTooltip} />
          <Legend />
          {yKeys.map((key, index) => (
            <Bar
              key={key}
              dataKey={key}
              name={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              fill={colors[index % colors.length]}
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          ))}
        </BarChart>
      );
    }

    if (type === 'pie_chart') {
      return (
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey={yKeys[0]}
            nameKey={xKey}
            label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip content={renderCustomTooltip} />
          <Legend />
        </PieChart>
      );
    }

    return (
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} tickFormatter={formatValue} />
        <Tooltip content={renderCustomTooltip} />
        <Legend />
        {yKeys.map((key, index) => (
          <Line key={key} type="monotone" dataKey={key} stroke={colors[index % colors.length]} strokeWidth={2} dot={false} />
        ))}
      </LineChart>
    );
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}