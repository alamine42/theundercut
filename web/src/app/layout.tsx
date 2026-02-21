import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Serif } from "next/font/google";
import { Agentation } from "agentation";
import { Providers } from "@/components/providers";
import "./globals.css";

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const ibmPlexSerif = IBM_Plex_Serif({
  variable: "--font-ibm-plex-serif",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "The Undercut",
  description: "F1 Analytics Dashboard - Race strategy, lap times, and championship standings",
  openGraph: {
    title: "The Undercut",
    description: "F1 Analytics Dashboard - Race strategy, lap times, and championship standings",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${ibmPlexMono.variable} ${ibmPlexSerif.variable} antialiased`}
      >
        <Providers>
          {children}
          {process.env.NODE_ENV === "development" && (
            <Agentation endpoint="http://localhost:4747" />
          )}
        </Providers>
      </body>
    </html>
  );
}
