import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { Footer } from "@/components/footer";
import { ToastHost } from "@/components/ios";
import { Nav } from "@/components/nav";
import { ServiceWorker } from "@/components/service-worker";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"] });

export const metadata: Metadata = {
 title: "Лихвомер — какво ще стане с вноската ми",
 description:
 "Следи европейските лихви и показва на прост български език какво означават те за вноската по вашия кредит.",
 manifest: "/manifest.webmanifest",
 appleWebApp: { capable: true, title: "Лихвомер", statusBarStyle: "default" },
};

export const viewport: Viewport = {
 themeColor: [
    // Лентата на браузъра следва темата, както прави всяко приложение на iOS.
    { media: "(prefers-color-scheme: light)", color: "#F5F6F8" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
 width: "device-width",
 initialScale: 1,
 viewportFit: "cover",
};

export default function RootLayout({
 children,
}: {
 children: React.ReactNode;
}) {
 return (
 <html lang="bg" suppressHydrationWarning>
 <head>
 {/* Прилага запазената тема преди първото рисуване, за да няма
 премигване от светло към тъмно при зареждане. */}
 <script
 dangerouslySetInnerHTML={{
 __html: `(function(){try{var s=localStorage.getItem("lihvomer_theme")||"system";var d=s==="dark"||(s==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.setAttribute("data-theme",d?"dark":"light");}catch(e){document.documentElement.setAttribute("data-theme","light");}})();`,
 }}
 />
 </head>
 <body className={inter.className}>
 <ServiceWorker />
 <ToastHost>
 <Nav />
 <main className="mx-auto w-full max-w-6xl px-4 pb-6 pt-5">
 {children}
 </main>
 <div className="pb-24 md:pb-0">
 <Footer />
 </div>
 </ToastHost>
 </body>
 </html>
 );
}
