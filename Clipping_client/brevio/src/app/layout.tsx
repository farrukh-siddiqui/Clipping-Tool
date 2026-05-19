import type { Metadata } from "next";
import { Inter, Instrument_Serif, Space_Grotesk } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-accent",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: {
    default: "Brevio — Turn Long Videos Into Viral Clips Automatically",
    template: "%s | Brevio",
  },
  description:
    "Brevio uses AI to find the most engaging moments in your podcasts, interviews, and streams — then delivers polished, caption-ready clips for TikTok, Reels, and Shorts.",
  keywords: [
    "AI video clipping",
    "viral clip extraction",
    "short form content",
    "podcast clips",
    "TikTok clips",
    "YouTube Shorts",
    "Instagram Reels",
    "AI video editor",
    "auto captions",
    "content repurposing",
    "Brevio",
  ],
  authors: [{ name: "Brevio" }],
  creator: "Brevio",
  metadataBase: new URL("https://brevio.ai"),
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://brevio.ai",
    siteName: "Brevio",
    title: "Brevio — Turn Long Videos Into Viral Clips Automatically",
    description:
      "AI-powered clip extraction for content creators. Find viral moments, add captions, reframe to vertical — all automatically.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Brevio — AI-Powered Clip Extraction",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Brevio — Turn Long Videos Into Viral Clips Automatically",
    description:
      "AI-powered clip extraction for content creators. Find viral moments, add captions, reframe to vertical — all automatically.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${spaceGrotesk.variable} ${instrumentSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
