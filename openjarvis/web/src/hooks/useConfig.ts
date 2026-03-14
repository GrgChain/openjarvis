import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "../lib/api";

export interface AgentSettings {
  model: string;
  provider: string;
  max_tokens: number;
  temperature: number;
  max_iterations: number;
  context_window_tokens: number;
  reasoning_effort: string;
  workspace: string;
}

export interface HeartbeatConfig {
  enabled: boolean;
  interval_s: number;
}

export interface GatewayConfig {
  host: string;
  port: number;
  heartbeat: HeartbeatConfig;
}

export interface GatewayConfigUpdate {
  host?: string;
  port?: number;
  heartbeat_enabled?: boolean;
  heartbeat_interval_s?: number;
}

export function useAgentSettings() {
  return useQuery<AgentSettings>({
    queryKey: ["config", "agent"],
    queryFn: () => api.get("/config/agent").then((r) => r.data),
  });
}

export function useUpdateAgentSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<AgentSettings>) =>
      api.patch("/config/agent", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config", "agent"] });
    },
  });
}

export function useGatewayConfig() {
  return useQuery<GatewayConfig>({
    queryKey: ["config", "gateway"],
    queryFn: () => api.get("/config/gateway").then((r) => r.data),
  });
}

export function useUpdateGatewayConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: GatewayConfigUpdate) =>
      api.patch("/config/gateway", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config", "gateway"] });
      toast.success("Saved");
    },
  });
}

export function useWorkspaceFile(name: string) {
  return useQuery<{ name: string; content: string }>({
    queryKey: ["config", "workspace-file", name],
    queryFn: () => api.get(`/config/workspace-file/${name}`).then((r) => r.data),
    enabled: !!name,
  });
}

export function useSaveWorkspaceFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      api.put(`/config/workspace-file/${name}`, { content }).then((r) => r.data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["config", "workspace-file", vars.name] });
      toast.success("Saved");
    },
  });
}

export async function exportWorkspace(): Promise<void> {
  const resp = await api.get("/config/workspace/export", { responseType: "blob" });
  const cd: string = resp.headers["content-disposition"] ?? "";
  const match = cd.match(/filename=([^\s;]+)/);
  const filename = match ? match[1] : "workspace.zip";
  const url = URL.createObjectURL(resp.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function useImportWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<{ ok: boolean; backup: string | null }>(
        "/config/workspace/import",
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      ).then((r) => r.data);
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["config", "workspace-file"] });
      const msg = data.backup
        ? `Import successful. Previous config backed up to: ${data.backup}`
        : "Import successful";
      toast.success(msg);
    },
    onError: () => toast.error("导入失败"),
  });
}

export interface WorkspaceTreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children?: WorkspaceTreeNode[];
}

export function useWorkspaceTree() {
  return useQuery<{ tree: WorkspaceTreeNode[] }>({
    queryKey: ["config", "workspace-tree"],
    queryFn: () => api.get("/config/workspace/tree").then((r) => r.data),
  });
}

export function useWorkspaceFileByPath(path: string) {
  return useQuery<{ name: string; path: string; content: string }>({
    queryKey: ["config", "workspace-file-path", path],
    queryFn: () => api.get("/config/workspace/file", { params: { path } }).then((r) => r.data),
    enabled: !!path,
  });
}

export function useSaveWorkspaceFileByPath() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) =>
      api.put("/config/workspace/file", { path, content }).then((r) => r.data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["config", "workspace-file-path", vars.path] });
      toast.success("Saved");
    },
  });
}

export function useDeleteWorkspaceFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) =>
      api.delete("/config/workspace/file", { params: { path } }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config", "workspace-tree"] });
    },
  });
}

export function useRawConfig() {
  return useQuery<{ content: string }>({
    queryKey: ["config", "raw"],
    queryFn: () => api.get("/config/raw").then((r) => r.data),
  });
}

export async function uploadFile(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post<{ url: string }>("/files/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data.url;
}

export function useSaveRawConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      api.put("/config/raw", { content }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
      toast.success("配置已保存");
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "保存失败";
      toast.error(msg);
    },
  });
}