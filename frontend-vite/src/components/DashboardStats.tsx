import { useMemo } from "react";
import { TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { UserBillingCredential } from "@/types";

interface DashboardStatsProps {
  credentials?: UserBillingCredential[];
}

export function DashboardStats({ credentials = [] }: DashboardStatsProps) {

  // Calculate real stats from credentials
  const stats = useMemo(() => {
    // Count unique providers (by utility_co_name)
    const uniqueProviders = new Set(
      credentials
        .filter(c => c.utility_co_name)
        .map(c => c.utility_co_name)
    );
    const totalProviders = uniqueProviders.size;
    const completed = credentials.filter(c => c.last_state?.toLowerCase() === "completed").length;
    const failed = credentials.filter(c => c.last_state?.toLowerCase() === "error").length;
    const active = credentials.filter(c => c.last_state?.toLowerCase() === "running").length;
    const idle = credentials.filter(c => c.last_state?.toLowerCase() === "idle").length;
    
    // Calculate average billing cycle days
    const cyclesWithDays = credentials.filter(c => c.billing_cycle_day).map(c => c.billing_cycle_day!);
    const avgCycleDays = cyclesWithDays.length > 0 
      ? Math.round(cyclesWithDays.reduce((a, b) => a + b, 0) / cyclesWithDays.length)
      : 0;
    
    // Calculate days until next billing (simplified - using average)
    const today = new Date();
    const currentDay = today.getDate();
    let daysUntil = 0;
    if (avgCycleDays > 0) {
      if (currentDay <= avgCycleDays) {
        daysUntil = avgCycleDays - currentDay;
      } else {
        const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
        daysUntil = daysInMonth - currentDay + avgCycleDays;
      }
    }
    
    return {
      totalProviders,
      completed,
      failed,
      active,
      idle,
      avgCycleDays,
      daysUntil,
    };
  }, [credentials]);

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 border border-border shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-muted-foreground">Total Providers</h3>
            <div className="flex items-center gap-1 text-success text-sm">
              <TrendingUp className="h-4 w-4" />
              <span>+5.2%</span>
            </div>
          </div>
          <div className="text-3xl font-semibold text-foreground mb-1">{stats.totalProviders}</div>
          <p className="text-xs text-muted-foreground">Active utility accounts</p>
        </Card>

        <Card className="p-6 border border-border shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-muted-foreground">Status Overview</h3>
            <div className="flex items-center gap-1 text-muted-foreground text-sm">
              <span>{stats.completed} completed</span>
            </div>
          </div>
          <div className="text-3xl font-semibold text-foreground mb-1">
            {stats.failed > 0 ? `${stats.failed} failed` : "All good"}
          </div>
          <p className="text-xs text-muted-foreground">
            {stats.active > 0 ? `${stats.active} active` : "No active processes"}
          </p>
        </Card>

        <Card className="p-6 border border-border shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-muted-foreground">Avg. Bill Cycle</h3>
            <div className="flex items-center gap-1 text-muted-foreground text-sm">
              <span>Stable</span>
            </div>
          </div>
          <div className="text-3xl font-semibold text-foreground mb-1">
            {stats.daysUntil > 0 ? `${stats.daysUntil} days` : "N/A"}
          </div>
          <p className="text-xs text-muted-foreground">Until next billing period</p>
        </Card>
      </div>

    </div>
  );
}

