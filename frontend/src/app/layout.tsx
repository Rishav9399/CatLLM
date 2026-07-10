import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Obsidian Core",
  description: "Advanced architectural intelligence environment.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      {/* We lock the body's dimensions and hide overflow. 
        The React application handles its own internal scrolling mechanics. 
      */}
      <body className="bg-[#030303] text-[#e5e5e5] w-full h-screen overflow-hidden selection:bg-indigo-900/40">
        {children}
      </body>
    </html>
  );
}