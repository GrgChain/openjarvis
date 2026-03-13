import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Download, Upload, FileJson, RefreshCw, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { useRawConfig, useSaveRawConfig, exportWorkspace, useImportWorkspace } from "../hooks/useConfig";

// ── JSON validation helper ─────────────────────────────────────────────────

function tryParseJson(text: string): { ok: true; formatted: string } | { ok: false; error: string } {
  try {
    const parsed = JSON.parse(text);
    return { ok: true, formatted: JSON.stringify(parsed, null, 2) };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// ── Raw Config Editor ─────────────────────────────────────────────────────────

function RawConfigEditor() {
  const { t } = useTranslation();
  const { data, isLoading, refetch } = useRawConfig();
  const save = useSaveRawConfig();

  const [content, setContent] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Initialize content when data loads
  if (data && content === null) {
    setContent(data.content);
    setDirty(false);
  }

  const handleChange = (v: string) => {
    setContent(v);
    setDirty(true);
    const result = tryParseJson(v);
    setJsonError(result.ok ? null : result.error);
  };

  const handleFormat = () => {
    if (!content) return;
    const result = tryParseJson(content);
    if (result.ok) {
      setContent(result.formatted);
      setJsonError(null);
      toast.success(t("sysconfig.formatted"));
    } else {
      toast.error(result.error);
    }
  };

  const handleSave = () => {
    if (!content || jsonError) return;
    save.mutate(content, {
      onSuccess: () => {
        setDirty(false);
        refetch();
      },
    });
  };

  const handleDiscard = () => {
    if (data) {
      setContent(data.content);
      setDirty(false);
      setJsonError(null);
    }
  };

  if (isLoading) {
    return <Skeleton className="h-[500px] w-full" />;
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 flex-1">
          <FileJson className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-muted-foreground">~/.nanobot/config.json</span>
          {dirty && (
            <Badge variant="outline" className="text-xs text-amber-600 border-amber-300 bg-amber-50">
              {t("settings.unsaved")}
            </Badge>
          )}
          {!dirty && !jsonError && content !== null && (
            <Badge variant="outline" className="text-xs text-green-600 border-green-300 bg-green-50">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              {t("sysconfig.synced")}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {jsonError && (
            <span className="flex items-center gap-1 text-xs text-destructive">
              <AlertCircle className="h-3.5 w-3.5" />
              {t("sysconfig.jsonError")}
            </span>
          )}
          <Button variant="ghost" size="sm" className="h-8 gap-1.5" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5" />
            {t("common.refresh")}
          </Button>
          <Button variant="outline" size="sm" className="h-8" onClick={handleFormat} disabled={!content || !dirty}>
            {t("sysconfig.format")}
          </Button>
          {dirty && (
            <Button variant="ghost" size="sm" className="h-8" onClick={handleDiscard}>
              {t("common.cancel")}
            </Button>
          )}
          <Button
            size="sm"
            className="h-8 gap-1.5"
            onClick={handleSave}
            disabled={!dirty || !!jsonError || save.isPending}
          >
            <Save className="h-3.5 w-3.5" />
            {t("common.save")}
          </Button>
        </div>
      </div>

      {/* Editor */}
      <div className="relative">
        <Textarea
          value={content ?? ""}
          onChange={(e) => handleChange(e.target.value)}
          className={`font-mono text-xs min-h-[520px] resize-y leading-relaxed ${
            jsonError ? "border-destructive focus-visible:ring-destructive" : ""
          }`}
          spellCheck={false}
        />
        {jsonError && (
          <p className="mt-1.5 text-xs text-destructive font-mono">{jsonError}</p>
        )}
      </div>
    </div>
  );
}

// ── Import / Export ───────────────────────────────────────────────────────────

function ImportExportPanel() {
  const { t } = useTranslation();
  const importRef = useRef<HTMLInputElement>(null);
  const importWs = useImportWorkspace();
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportWorkspace();
      toast.success(t("sysconfig.exportSuccess"));
    } catch {
      toast.error(t("sysconfig.exportError"));
    } finally {
      setExporting(false);
    }
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    importWs.mutate(file);
    e.target.value = "";
  };

  return (
    <div className="space-y-4 max-w-xl">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Download className="h-4 w-4 text-sky-500" />
            {t("sysconfig.export")}
          </CardTitle>
          <CardDescription className="text-xs">
            {t("sysconfig.exportDesc")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="gap-2"
            onClick={handleExport}
            disabled={exporting}
          >
            <Download className="h-4 w-4" />
            {exporting ? t("common.loading") : t("sysconfig.exportBtn")}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Upload className="h-4 w-4 text-amber-500" />
            {t("sysconfig.import")}
          </CardTitle>
          <CardDescription className="text-xs">
            {t("sysconfig.importDesc")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => importRef.current?.click()}
            disabled={importWs.isPending}
          >
            <Upload className="h-4 w-4" />
            {importWs.isPending ? t("common.loading") : t("sysconfig.importBtn")}
          </Button>
          <input ref={importRef} type="file" accept=".zip" hidden onChange={handleImport} />
          <p className="mt-2 text-xs text-muted-foreground">{t("sysconfig.importHint")}</p>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SystemConfig() {
  const { t } = useTranslation();

  return (
    <Tabs defaultValue="editor">
      <TabsList>
        <TabsTrigger value="editor">{t("sysconfig.tabEditor")}</TabsTrigger>
        <TabsTrigger value="backup">{t("sysconfig.tabBackup")}</TabsTrigger>
      </TabsList>

      <TabsContent value="editor" className="mt-4">
        <RawConfigEditor />
      </TabsContent>

      <TabsContent value="backup" className="mt-4">
        <ImportExportPanel />
      </TabsContent>
    </Tabs>
  );
}
