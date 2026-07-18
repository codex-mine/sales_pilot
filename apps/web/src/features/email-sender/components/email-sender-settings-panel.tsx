"use client";

import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Switch } from "@/components/ui/switch";
import { AlertTriangle, Mail, Unlock } from "@/icons";
import {
  useConnectEmailSender,
  useDisconnectEmailSender,
  useEmailSenderSettings,
} from "../hooks/use-email-sender-settings";

/** Trigger-action + a small connect form — no Zod schema needed here, same
 * reasoning `ai/schemas/index.ts` documents for job triggers: this isn't a
 * record being created and edited later, just credentials submitted once. */
export function EmailSenderSettingsPanel(): React.ReactElement {
  const { settings, isLoading, isError, errorMessage, refetch } = useEmailSenderSettings();
  const { connect, isConnecting } = useConnectEmailSender();
  const { disconnect, isDisconnecting } = useDisconnectEmailSender();
  const disconnectConfirm = useConfirmDialog();

  const [host, setHost] = useState("");
  const [port, setPort] = useState("587");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [dailyLimit, setDailyLimit] = useState("");

  async function handleConnect(): Promise<void> {
    await connect({
      host, port: Number(port) || 587, username: username || undefined, password, use_tls: useTls,
      daily_send_limit: dailyLimit ? Number(dailyLimit) : undefined,
    });
    setPassword("");
  }

  async function handleDisconnect(): Promise<void> {
    if (!settings?.integration_id) return;
    await disconnect(settings.integration_id);
    disconnectConfirm.close();
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError || !settings) {
    return <ErrorState title="Couldn't load sender settings" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  const nearLimit = settings.sent_today >= settings.daily_send_limit * 0.8;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="size-4" />
            Sending mailbox
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <StatusBadge tone={settings.is_connected ? "success" : "neutral"}>
                {settings.is_connected ? "Connected" : "Not connected"}
              </StatusBadge>
              {!settings.is_connected && settings.has_platform_fallback && (
                <span className="text-body-sm text-muted-foreground">Using the platform default mailbox.</span>
              )}
            </div>
            {settings.is_connected && (
              <Button variant="outline" size="sm" onClick={disconnectConfirm.open}>
                <Unlock className="size-4" />
                Disconnect
              </Button>
            )}
          </div>

          {settings.is_connected && (
            <dl className="grid grid-cols-1 gap-3 text-body-sm sm:grid-cols-2">
              <div>
                <dt className="text-caption text-muted-foreground">Host</dt>
                <dd className="text-foreground">{settings.host}:{settings.port}</dd>
              </div>
              <div>
                <dt className="text-caption text-muted-foreground">Username</dt>
                <dd className="text-foreground">{settings.username || "—"}</dd>
              </div>
            </dl>
          )}

          <div className="flex flex-col gap-1">
            <span className="text-body-sm text-muted-foreground">
              Sent today: <span className="font-medium text-foreground">{settings.sent_today}</span> of{" "}
              {settings.daily_send_limit}
            </span>
          </div>

          {nearLimit && (
            <Alert variant="warning">
              <AlertTriangle className="size-4" />
              <AlertTitle>Approaching daily send limit</AlertTitle>
              <AlertDescription>
                New sends will be automatically deferred to the next window once the limit is reached.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{settings.is_connected ? "Reconnect a different mailbox" : "Connect a sending mailbox"}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label required>SMTP host</Label>
              <Input placeholder="smtp.example.com" value={host} onChange={(e) => setHost(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label required>Port</Label>
              <Input type="number" value={port} onChange={(e) => setPort(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Username</Label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label required>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Daily send limit</Label>
              <Input
                type="number"
                placeholder={String(settings.daily_send_limit)}
                value={dailyLimit}
                onChange={(e) => setDailyLimit(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2 pt-6">
              <Switch checked={useTls} onCheckedChange={setUseTls} />
              <Label className="mb-0">Use TLS</Label>
            </div>
          </div>
          <div>
            <Button onClick={() => void handleConnect()} isLoading={isConnecting} disabled={!host || !password}>
              Connect
            </Button>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={disconnectConfirm.isOpen}
        onOpenChange={disconnectConfirm.onOpenChange}
        title="Disconnect this sending mailbox?"
        description="Outreach emails will fall back to the platform default mailbox, if one is configured, or fail to send until a new mailbox is connected."
        confirmLabel="Disconnect"
        isConfirming={isDisconnecting}
        onConfirm={handleDisconnect}
      />
    </div>
  );
}
