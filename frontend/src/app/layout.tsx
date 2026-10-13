import type { Metadata, Viewport } from "next";
import "@/styles/global.css";
import Providers from "@/components/shared/Providers";
export const metadata: Metadata = {
  title: "CodeBuddy — AI Codebase Understanding",
  description:
    "Explore your repository, ask questions, and inspect answers backed by real source code.",
  icons: { icon: "/favicon.svg" },
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#000000",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900&amp;family=Instrument+Serif:ital@1&amp;display=swap"
        />
      </head>
      <body style={{ background: "#000", color: "#fff" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
