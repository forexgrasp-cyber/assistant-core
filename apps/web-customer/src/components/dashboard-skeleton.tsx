/**
 * Dashboard Skeleton Loader
 */

export function DashboardSkeleton() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar Skeleton */}
      <aside className="w-64 bg-card border-r border-border flex flex-col hidden lg:flex">
        <div className="p-4 border-b border-border">
          <div className="h-6 w-3/4 bg-muted animate-pulse rounded mb-2" />
          <div className="h-4 w-1/2 bg-muted animate-pulse rounded" />
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 w-full bg-muted animate-pulse rounded" />
          ))}
        </nav>
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-muted animate-pulse" />
            <div className="flex-1">
              <div className="h-4 w-3/4 bg-muted animate-pulse rounded mb-1" />
              <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Skeleton */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-card border-b border-border">
          <div className="h-full flex items-center px-6">
            <div className="h-6 w-32 bg-muted animate-pulse rounded" />
          </div>
        </header>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* KPI Cards Skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-card border border-border rounded-lg p-5 animate-pulse">
                <div className="h-4 w-1/3 bg-muted rounded mb-3" />
                <div className="h-8 w-1/2 bg-muted rounded" />
              </div>
            ))}
          </div>

          {/* Charts Skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[1, 2].map((i) => (
              <div key={i} className="bg-card border border-border rounded-lg p-6 h-96 animate-pulse">
                <div className="h-5 w-1/3 bg-muted rounded mb-4" />
                <div className="h-full bg-muted rounded" />
              </div>
            ))}
          </div>

          {/* Reports Table Skeleton */}
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <div className="p-4 border-b border-border">
              <div className="h-5 w-1/4 bg-muted animate-pulse rounded" />
            </div>
            <div className="divide-y divide-border">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="p-4 flex items-center justify-between animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded bg-muted" />
                    <div className="flex flex-col gap-1">
                      <div className="h-4 w-32 bg-muted rounded" />
                      <div className="h-3 w-24 bg-muted rounded" />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-20 bg-muted rounded" />
                    <div className="h-8 w-20 bg-muted rounded" />
                    <div className="h-8 w-20 bg-muted rounded" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}