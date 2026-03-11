import './globals.css';
import HitlDrawerWrapper from '@/components/HitlDrawerWrapper';
import { HelixSocketProvider } from '@/hooks/useHelixSocket';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased h-screen overflow-hidden bg-[#1a1a1a] text-foreground">
        <HelixSocketProvider>
          {children}
          <HitlDrawerWrapper />
        </HelixSocketProvider>
      </body>
    </html>
  );
}
