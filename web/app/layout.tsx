import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FIND EVIL — autonomous DFIR at machine speed",
  description:
    "A local, defensive autonomous SOC where math decides, a signed ledger records, and the LLM only explains. SANS Find Evil! — Custom MCP Server (Approach #2).",
  openGraph: {
    title: "FIND EVIL — autonomous DFIR at machine speed",
    description:
      "Math decides, the ledger records, the LLM only explains. Tamper-evident forensic evidence from an agent that cannot run arbitrary commands.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
