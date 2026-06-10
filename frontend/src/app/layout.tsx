import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RegLoop AI",
  description: "Regulatory compliance review — automated.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
