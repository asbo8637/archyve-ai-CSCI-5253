import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Archyve AI",
  description: "Secure, company-scoped document workflows for B2B teams."
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
