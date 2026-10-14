import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "ProofPatch",
  description: "Evidence before optimization. Human approval before GitHub.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            <span className="brand-mark">
              p<span>✓</span>
            </span>
            ProofPatch
          </Link>
          <span className="header-note">PYTHON PERFORMANCE WORKBENCH</span>
          <span className="version">v1.0 / local</span>
        </header>
        {children}
        <footer className="site-footer">
          <span>LLM proposes. Deterministic harness decides.</span>
          <span>Two human gates. One evidence trail.</span>
        </footer>
      </body>
    </html>
  );
}
