import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AssessmentProvider } from '../context/AssessmentContext';
import DashboardShell from '../components/DashboardShell';
import './globals.css';

import { Suspense } from 'react';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI Agent Reliability Dashboard',
  description:
    'An AI-powered reliability engine that understands an agent\'s capabilities, automatically generates targeted adversarial tests, safely executes them, explains failures, scores risk, and continuously converts discovered failures into regression tests.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-zinc-950 text-zinc-50 min-h-screen`}>
        <Suspense fallback={<div className="p-8 text-xs font-mono text-zinc-500">Loading...</div>}>
          <AssessmentProvider>
            <DashboardShell>{children}</DashboardShell>
          </AssessmentProvider>
        </Suspense>
      </body>
    </html>
  );
}
