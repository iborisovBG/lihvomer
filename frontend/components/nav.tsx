"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
 Bell,
 Calculator,
 Gauge,
 HeartPulse,
 Landmark,
 LogOut,
 Newspaper,
 Wallet,
} from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { clearToken, getToken } from "@/lib/api";
import { cn } from "@/lib/utils";

const LINKS = [
 { href: "/", label: "Табло", icon: Gauge },
 { href: "/loans", label: "Кредити", icon: Wallet },
 { href: "/health", label: "Моят кредит", icon: HeartPulse },
 { href: "/alerts", label: "Известия", icon: Bell },
 { href: "/state", label: "Държавата", icon: Landmark },
 { href: "/news", label: "Новини", icon: Newspaper },
 { href: "/calculator", label: "Калкулатор", icon: Calculator },
];

export function Nav() {
 const pathname = usePathname();
 const router = useRouter();
 const [signedIn, setSignedIn] = useState(false);

 useEffect(() => {
 setSignedIn(getToken() !== null);
 }, [pathname]);

 function signOut() {
 clearToken();
 setSignedIn(false);
 router.push("/login");
 }

 return (
 <>
 <header className="sticky top-0 z-30 glass-bar border-b">
 <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
 <Link href="/" className="flex items-center gap-2">
 <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
 <Gauge className="h-4 w-4" />
 </span>
 <span className="type-title-3">Лихвомер</span>
 </Link>

 <nav className="hidden items-center gap-0.5 lg:flex">
 {LINKS.map(({ href, label }) => (
 <Link
 key={href}
 href={href}
 className={cn(
 "whitespace-nowrap rounded-lg px-2.5 py-2 type-subhead font-medium transition-colors",
 pathname === href
 ? "bg-accent text-primary"
 : "text-muted-foreground hover:bg-muted hover:text-foreground",
 )}
 >
 {label}
 </Link>
 ))}
 </nav>

 <div className="flex items-center gap-2">
 <ThemeToggle />
 <Link
 href="/sources"
 className={cn(
 "hidden rounded-lg px-3 py-2 type-subhead font-medium transition-colors sm:block",
 pathname === "/sources"
 ? "bg-accent text-primary"
 : "text-muted-foreground hover:bg-muted hover:text-foreground",
 )}
 >
 Източници
 </Link>
 {signedIn ? (
 <button
 type="button"
 onClick={signOut}
 className="flex items-center gap-1.5 rounded-lg px-3 py-2 type-subhead font-medium text-muted-foreground hover:text-foreground"
 >
 <LogOut className="h-4 w-4" />
 <span className="hidden sm:inline">Изход</span>
 </button>
 ) : (
 <Link
 href="/login"
 className="rounded-lg bg-primary px-4 py-2 type-subhead font-medium text-primary-foreground transition-colors hover:bg-primary/90"
 >
 Вход
 </Link>
 )}
 </div>
 </div>
 </header>

 <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 glass-bar border-t md:hidden">
 {LINKS.slice(0, 4).map(({ href, label, icon: Icon }) => (
 <Link
 key={href}
 href={href}
 className={cn(
 "flex flex-col items-center gap-1 py-2.5 type-caption font-medium",
 pathname === href ? "text-primary" : "text-muted-foreground",
 )}
 >
 <Icon className="h-5 w-5" />
 {label}
 </Link>
 ))}
 </nav>
 </>
 );
}
