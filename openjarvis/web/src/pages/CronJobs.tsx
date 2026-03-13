import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useCronJobs,
  useCreateCronJob,
  useUpdateCronJob,
  useDeleteCronJob,
  useToggleCronJob,
  type CronJob,
  type CronJobRequest,
  type CronSchedule,
} from "../hooks/useCron";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Textarea } from "../components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { ConfirmDialog } from "../components/shared/ConfirmDialog";
import { Skeleton } from "../components/ui/skeleton";
import { Plus, Pencil, Trash2 } from "lucide-react";

function formatMs(ms: number | null | undefined): string {
  if (!ms) return "-";
  return new Date(ms).toLocaleString();
}

function exprFromSchedule(s: CronSchedule): string {
  if (s.kind === "cron" && s.expr) return s.expr;
  if (s.kind === "every" && s.every_ms) return `every ${Math.round(s.every_ms / 1000)}s`;
  if (s.kind === "at" && s.at_ms) return `at ${formatMs(s.at_ms)}`;
  return "-";
}

/** Parse a 5-field cron expression into parts, return null if invalid */
function parseCronExpr(expr: string): { minute: string; hour: string; day: string; month: string; weekday: string } | null {
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) return null;
  return { minute: parts[0], hour: parts[1], day: parts[2], month: parts[3], weekday: parts[4] };
}

function CronForm({
  initial,
  onSave,
  onClose,
}: {
  initial?: CronJob;
  onSave: (data: CronJobRequest) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(initial?.name ?? "");
  const [kind, setKind] = useState<CronSchedule["kind"]>(initial?.schedule.kind ?? "cron");

  // cron expr fields
  const initParts = initial?.schedule.expr ? parseCronExpr(initial.schedule.expr) : null;
  const [minute, setMinute] = useState(initParts?.minute ?? "*");
  const [hour, setHour] = useState(initParts?.hour ?? "*");
  const [day, setDay] = useState(initParts?.day ?? "*");
  const [month, setMonth] = useState(initParts?.month ?? "*");
  const [weekday, setWeekday] = useState(initParts?.weekday ?? "*");

  // every interval
  const [everySeconds, setEverySeconds] = useState(
    initial?.schedule.every_ms ? String(Math.round(initial.schedule.every_ms / 1000)) : "60"
  );

  const [message, setMessage] = useState(initial?.payload.message ?? "");
  const [deliver, setDeliver] = useState(initial?.payload.deliver ?? false);
  const [channel, setChannel] = useState(initial?.payload.channel ?? "");
  const [to, setTo] = useState(initial?.payload.to ?? "");
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);

  const handleSave = () => {
    let schedule: CronSchedule;
    if (kind === "cron") {
      schedule = { kind: "cron", expr: `${minute} ${hour} ${day} ${month} ${weekday}` };
    } else if (kind === "every") {
      schedule = { kind: "every", every_ms: Number(everySeconds) * 1000 };
    } else {
      schedule = { kind: "at", at_ms: Date.now() + 60000 };
    }
    onSave({
      name,
      enabled,
      schedule,
      payload: { message, deliver, channel: channel || undefined, to: to || undefined },
    });
  };

  const cronField = (label: string, value: string, onChange: (v: string) => void) => (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <Input
        className="font-mono text-sm h-8"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );

  return (
    <>
      <div className="space-y-4 py-2">
        <div className="space-y-1">
          <Label>{t("cron.name")}</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>

        <div className="space-y-2">
          <Label>{t("cron.schedule")}</Label>
          <Select value={kind} onValueChange={(v) => setKind(v as CronSchedule["kind"])}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="cron">Cron</SelectItem>
              <SelectItem value="every">Every (interval)</SelectItem>
            </SelectContent>
          </Select>

          {kind === "cron" && (
            <>
              <div className="grid grid-cols-5 gap-2">
                {cronField(t("cron.minute"), minute, setMinute)}
                {cronField(t("cron.hour"), hour, setHour)}
                {cronField(t("cron.day"), day, setDay)}
                {cronField(t("cron.month"), month, setMonth)}
                {cronField(t("cron.weekday"), weekday, setWeekday)}
              </div>
              <p className="text-xs text-muted-foreground">
                <code className="font-mono">{`${minute} ${hour} ${day} ${month} ${weekday}`}</code>
              </p>
            </>
          )}

          {kind === "every" && (
            <div className="space-y-1">
              <Label className="text-xs">{t("cron.intervalSeconds")}</Label>
              <Input
                type="number"
                className="font-mono text-sm h-8 max-w-[200px]"
                value={everySeconds}
                onChange={(e) => setEverySeconds(e.target.value)}
                min={1}
              />
            </div>
          )}
        </div>

        <div className="space-y-1">
          <Label>{t("cron.message")}</Label>
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
          />
        </div>
        <div className="flex items-center gap-3">
          <Switch checked={deliver} onCheckedChange={setDeliver} id="deliver" />
          <Label htmlFor="deliver">Deliver to channel</Label>
        </div>
        {deliver && (
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Channel</Label>
              <Input value={channel} onChange={(e) => setChannel(e.target.value)} placeholder="telegram" />
            </div>
            <div className="space-y-1">
              <Label>To</Label>
              <Input value={to} onChange={(e) => setTo(e.target.value)} placeholder="chat_id" />
            </div>
          </div>
        )}
        <div className="flex items-center gap-3">
          <Switch checked={enabled} onCheckedChange={setEnabled} id="enabled" />
          <Label htmlFor="enabled">{enabled ? t("cron.enabled") : t("cron.disabled")}</Label>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
        <Button onClick={handleSave} disabled={!name || !message}>{t("cron.save")}</Button>
      </DialogFooter>
    </>
  );
}

export default function CronJobs() {
  const { t } = useTranslation();
  const { data: jobs, isLoading } = useCronJobs();
  const create = useCreateCronJob();
  const update = useUpdateCronJob();
  const del = useDeleteCronJob();
  const toggle = useToggleCronJob();

  const [mode, setMode] = useState<"create" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<CronJob | null>(null);
  const [delTarget, setDelTarget] = useState<string | null>(null);

  const handleSave = (data: CronJobRequest) => {
    if (mode === "create") {
      create.mutate(data);
    } else if (editTarget) {
      update.mutate({ id: editTarget.id, ...data });
    }
    setMode(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setEditTarget(null); setMode("create"); }}>
          <Plus className="mr-2 h-4 w-4" />
          {t("cron.add")}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("cron.name")}</TableHead>
                <TableHead>{t("cron.schedule")}</TableHead>
                <TableHead>{t("cron.nextRun")}</TableHead>
                <TableHead className="w-24 text-center">{t("cron.enabled")}</TableHead>
                <TableHead className="w-20 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs?.map((j) => (
                <TableRow key={j.id}>
                  <TableCell className="font-medium">{j.name}</TableCell>
                  <TableCell className="font-mono text-xs">{exprFromSchedule(j.schedule)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatMs(j.state.next_run_at_ms)}
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={j.enabled}
                      disabled={toggle.isPending}
                      onCheckedChange={(enabled) => toggle.mutate({ id: j.id, job: j, enabled })}
                    />
                  </TableCell>
                  <TableCell className="text-right space-x-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => { setEditTarget(j); setMode("edit"); }}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-destructive"
                      onClick={() => setDelTarget(j.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {(!jobs || jobs.length === 0) && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">{t("common.noData")}</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={!!mode} onOpenChange={(v) => !v && setMode(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{mode === "create" ? t("cron.add") : t("cron.edit")}</DialogTitle>
          </DialogHeader>
          <CronForm
            initial={editTarget ?? undefined}
            onSave={handleSave}
            onClose={() => setMode(null)}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!delTarget}
        title={t("cron.delete")}
        description={t("cron.deleteConfirm")}
        destructive
        onConfirm={() => { if (delTarget) del.mutate(delTarget); setDelTarget(null); }}
        onCancel={() => setDelTarget(null)}
      />
    </div>
  );
}
