import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";

export interface CronSchedule {
  kind: "at" | "every" | "cron";
  at_ms?: number | null;
  every_ms?: number | null;
  expr?: string | null;
  tz?: string | null;
}

export interface CronPayload {
  message: string;
  deliver?: boolean;
  channel?: string | null;
  to?: string | null;
}

export interface CronState {
  next_run_at_ms: number | null;
  last_run_at_ms: number | null;
  last_status: string | null;
  last_error: string | null;
}

export interface CronJob {
  id: string;
  name: string;
  enabled: boolean;
  schedule: CronSchedule;
  payload: CronPayload;
  state: CronState;
  delete_after_run: boolean;
  created_at_ms: number;
  updated_at_ms: number;
}

export interface CronJobRequest {
  name: string;
  enabled?: boolean;
  schedule: CronSchedule;
  payload: CronPayload;
  delete_after_run?: boolean;
}

export function useCronJobs() {
  return useQuery<CronJob[]>({
    queryKey: ["cron", "jobs"],
    queryFn: () => api.get("/cron/jobs").then((r) => r.data),
    refetchInterval: 30000,
  });
}

export function useCreateCronJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CronJobRequest) =>
      api.post("/cron/jobs", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron", "jobs"] });
      toast.success("Created");
    },
  });
}

export function useUpdateCronJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & CronJobRequest) =>
      api.put(`/cron/jobs/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron", "jobs"] });
      toast.success("Saved");
    },
  });
}

export function useDeleteCronJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/cron/jobs/${id}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron", "jobs"] });
      toast.success("Deleted");
    },
  });
}

export function useToggleCronJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, job, enabled }: { id: string; job: CronJob; enabled: boolean }) => {
      const req: CronJobRequest = {
        name: job.name,
        enabled,
        schedule: job.schedule,
        payload: job.payload,
        delete_after_run: job.delete_after_run,
      };
      return api.put(`/cron/jobs/${id}`, req).then((r) => r.data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cron", "jobs"] });
    },
  });
}
