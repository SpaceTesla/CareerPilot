import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";
import { ErrorBoundary } from "@/components/error-boundary";
import { Toaster } from "@/components/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CareerPilot",
  description: "AI-powered career guidance and resume analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ErrorBoundary>
          <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
            <QueryProvider>
              {children}
              <Toaster />
            </QueryProvider>
          </ThemeProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
