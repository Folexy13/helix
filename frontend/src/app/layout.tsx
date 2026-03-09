import './globals.css';
import Sidebar from '@/components/Sidebar';
import HitlDrawerWrapper from '@/components/HitlDrawerWrapper';
import { HelixSocketProvider } from '@/hooks/useHelixSocket';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased flex h-screen overflow-hidden bg-[#020617] text-foreground">
        <HelixSocketProvider>
          <Sidebar />
          <main className="flex-1 flex flex-col min-w-0">
            {children}
          </main>
          <HitlDrawerWrapper />
        </HelixSocketProvider>
      </body>
    </html>
  );
}
