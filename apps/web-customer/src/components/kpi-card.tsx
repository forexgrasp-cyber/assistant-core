/**
 * KPI Card Component
 */

'use client';

import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatNumber } from '@/lib/utils';

interface KPICardProps {
  label: string;
  value: string | number;
  trend?: number;
  format?: 'currency' | 'number' | 'percent' | 'ratio';
  icon?: React.ReactNode;
  className?: string;
}

export function KPICard({ label, value, trend, format = 'number', icon, className }: KPICardProps) {
  const trendIcon = trend !== undefined && trend !== 0
    ? trend > 0
      ? <TrendingUp className="w-4 h-4 text-success-600" />
      : <TrendingDown className="w-4 h-4 text-danger-600" />
    : <Minus className="w-4 h-4 text-muted-foreground" />;

  const trendClass = trend !== undefined && trend !== 0
    ? trend > 0
      ? 'text-success-600'
      : 'text-danger-600'
    : 'text-muted-foreground';

  const formattedValue = typeof value === 'string' ? value : formatNumber(value, format);

  return (
    <div className={`bg-card border border-border rounded-xl p-5 transition-shadow hover:shadow-md ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-muted-foreground truncate">{label}</p>
          <p className="text-2xl font-bold text-foreground mt-1">{formattedValue}</p>
          {trend !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              <span className={`text-sm font-medium ${trendClass}`}>
                {trendIcon}
                {trend > 0 ? '+' : ''}{trend.toFixed(1)}%
              </span>
              <span className="text-xs text-muted-foreground">vs last period</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}