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
  title: "CatLLM — Neural Interface",
  description: "Advanced AI assistant with RAG and multi-modal capabilities.",
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
      <body className="bg-[#050508] text-[#e8e8f0] w-full h-screen overflow-hidden selection:bg-indigo-900/40">
        {children}
      </body>
    </html>
  );
}