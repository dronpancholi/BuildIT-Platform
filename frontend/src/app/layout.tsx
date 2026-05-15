import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Providers } from "./providers";
import { CommandCenter } from "@/components/operational/command-center";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter", 
});

export const metadata: Metadata = {
  title: "BuildIT | Enterprise SEO Operations",
  description: "AI proposes. Deterministic systems execute.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={cn(inter.variable, "font-sans bg-surface-darker text-slate-300 min-h-screen")}>
        <Providers>
          {children}
          <CommandCenter />
        </Providers>
      </body>
    </html>
  );
}
