import { AppShell } from "@/components/layouts/app-shell";
import { Card } from "@/components/ui/card";
export default function SettingsPage(): React.ReactElement { return <AppShell><h1 className="mb-6 text-2xl font-semibold">Settings</h1><Card><h2 className="font-medium">Workspace settings</h2><p className="mt-2 text-sm text-slate-500">Organization settings will be configured here.</p></Card></AppShell>; }
