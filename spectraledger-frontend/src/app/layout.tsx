import type { Metadata } from "next";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/600.css";
import "@fontsource/jetbrains-mono/700.css";
import "./globals.css";
import AppProviders from "@/providers/AppProviders";

// Fonts are self-hosted via @fontsource (bundled at build time, no runtime
// fetch to Google Fonts) so the app never depends on reaching an external
// font host — important for both this build environment and any judge's
// network on demo day.

export const metadata: Metadata = {
  title: "SpectraLedger — Autonomous 5G Spectrum Clearinghouse",
  description:
    "A live B2B spot market for idle private 5G bandwidth: autonomous agents forecast, price, and clear trades between enterprises in real time.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
