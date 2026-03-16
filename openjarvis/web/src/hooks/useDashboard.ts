import { useQuery } from "@tanstack/react-query";
import api from "../lib/api";

export interface ChannelSummary {
  name: string;
  enabled: boolean;
  running: boolean;
  error: string | null;
}

export interface DashboardStats {
  channels: ChannelSummary[];
  running_channels: number;
  total_channels: number;
  enabled_cron: number;
  total_cron: number;
}

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: () => api.get("/dashboard/stats").then((r) => r.data),
    refetchInterval: 30000,
  });
}
