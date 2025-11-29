import type { Metadata, Viewport } from 'next';
import { Rethink_Sans } from 'next/font/google';
import { AppLayout } from '@/components/app-layout';
import './globals.css';

const geistSans = Rethink_Sans({
  variable: '--font-rethink-sans',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Legal Council | Virtual Deliberation Room',
  description:
    'AI-powered virtual judge panel for comprehensive legal case analysis and deliberation. Explore strict, humanist, and historical perspectives.',
  keywords: [
    'legal tech',
    'ai judge',
    'legal deliberation',
    'law',
    'justice',
    'virtual court',
    'legal opinion',
  ],
  authors: [{ name: 'Legal Council Team' }],
  openGraph: {
    title: 'Legal Council | Virtual Deliberation Room',
    description:
      'AI-powered virtual judge panel for comprehensive legal case analysis and deliberation.',
    url: 'https://legal-council.vercel.app', // Placeholder URL
    siteName: 'Legal Council',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Legal Council | Virtual Deliberation Room',
    description:
      'AI-powered virtual judge panel for comprehensive legal case analysis and deliberation.',
  },
};

export const viewport: Viewport = {
  themeColor: '#ffffff',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en'>
      <body className={`${geistSans.className} antialiased`}>
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  );
}
