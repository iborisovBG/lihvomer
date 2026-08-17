"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
 Alert,
 Button,
 Card,
 CardContent,
 CardDescription,
 CardHeader,
 CardTitle,
 Input,
 Label,
} from "@/components/ui";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
 const router = useRouter();
 const [mode, setMode] = useState<"login" | "register">("login");
 const [email, setEmail] = useState("");
 const [password, setPassword] = useState("");
 const [error, setError] = useState<string | null>(null);
 const [busy, setBusy] = useState(false);

 async function submit(event: React.FormEvent) {
 event.preventDefault();
 setError(null);
 setBusy(true);
 try {
 const result =
 mode === "login"
 ? await api.login(email, password)
 : await api.register(email, password);
 setToken(result.access_token);
 router.push("/loans");
 } catch (err) {
 setError((err as Error).message);
 } finally {
 setBusy(false);
 }
 }

 return (
 <div className="mx-auto max-w-md pt-8">
 <Card>
 <CardHeader>
 <CardTitle>
 {mode === "login" ? "Вход в профила" : "Създаване на профил"}
 </CardTitle>
 <CardDescription>
 Профилът служи само за да пазим вашите кредити и да смятаме
 вноските ви.
 </CardDescription>
 </CardHeader>
 <CardContent>
 <form onSubmit={submit} className="space-y-4">
 <div>
 <Label htmlFor="email">Имейл</Label>
 <Input
 id="email"
 type="email"
 autoComplete="email"
 required
 value={email}
 onChange={(e) => setEmail(e.target.value)}
 placeholder="ivan@example.com"
 />
 </div>
 <div>
 <Label htmlFor="password">Парола</Label>
 <Input
 id="password"
 type="password"
 autoComplete={
 mode === "login" ? "current-password" : "new-password"
 }
 required
 minLength={8}
 value={password}
 onChange={(e) => setPassword(e.target.value)}
 placeholder="поне 8 знака"
 />
 </div>

 {error && <Alert tone="bad">{error}</Alert>}

 <Button type="submit" className="w-full" disabled={busy}>
 {busy
 ? "Момент..."
 : mode === "login"
 ? "Влизане"
 : "Създаване на профил"}
 </Button>
 </form>

 <button
 type="button"
 onClick={() => {
 setMode(mode === "login" ? "register" : "login");
 setError(null);
 }}
 className="mt-4 w-full text-center type-subhead text-primary hover:underline"
 >
 {mode === "login"
 ? "Нямате профил? Създайте нов."
 : "Вече имате профил? Влезте."}
 </button>
 </CardContent>
 </Card>
 </div>
 );
}
