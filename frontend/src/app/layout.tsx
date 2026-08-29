import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO/AEO Audit Agent",
  description: "Evidence-backed, prioritized website search audits.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
