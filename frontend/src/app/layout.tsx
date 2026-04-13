import type { Metadata } from "next";
import { Cinzel, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const cinzel = Cinzel({
  variable: "--font-cinzel",
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Albion Craft Ranker",
  description: "Classifique itens craftáveis por lucratividade em todas as cidades de Albion Online",
};

function AppHeader() {
  return (
    <header
      className="sticky top-0 z-30 border-b px-4 py-3 md:px-8"
      style={{
        background: "var(--color-bg-elevated)",
        borderColor: "var(--color-border-default)",
      }}
    >
      <div className="mx-auto flex max-w-[1600px] items-center justify-between">
        <div className="flex items-center gap-3">
          <h1
            className="text-xl font-bold tracking-wide md:text-2xl"
            style={{
              fontFamily: "var(--font-cinzel), Cinzel, Georgia, serif",
              color: "var(--color-accent-gold)",
            }}
          >
            Albion Craft Ranker
          </h1>
          <span
            className="rounded px-2 py-0.5 text-xs font-medium"
            style={{
              background: "var(--color-bg-overlay)",
              color: "var(--color-text-secondary)",
              border: "1px solid var(--color-border-default)",
            }}
          >
            Oeste
          </span>
        </div>
        <div
          className="flex items-center gap-2 text-xs"
          style={{ color: "var(--color-text-muted)" }}
        >
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: "var(--color-profit-strong)" }}
            aria-label="Dados atualizados"
          />
          Ao Vivo
        </div>
      </div>
    </header>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${cinzel.variable} ${plexSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <AppHeader />
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-6 md:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
