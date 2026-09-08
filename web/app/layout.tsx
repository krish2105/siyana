import type { Metadata, Viewport } from "next";
import { Archivo, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { SmoothScroll } from "@/components/providers/SmoothScroll";
import { UiStateProvider } from "@/components/providers/UiState";

const archivo = Archivo({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-archivo",
  display: "swap",
});
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SIYANA · MIRAAT control room",
  description:
    "Continuing-airworthiness intelligence: recurring defect signatures, remaining useful life, hangar scheduling and evidence for every recommendation.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0F1E27" },
    { media: "(prefers-color-scheme: light)", color: "#E4E6E3" },
  ],
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const jar = await cookies();
  const theme = jar.get("theme")?.value === "ramp" ? "ramp" : "hangar";
  return (
    <html
      lang="en"
      data-theme={theme}
      className={`${archivo.variable} ${plexSans.variable} ${plexMono.variable} h-full`}
    >
      <body className="min-h-full flex flex-col">
        <UiStateProvider initialTheme={theme}>
          <SmoothScroll>{children}</SmoothScroll>
        </UiStateProvider>
      </body>
    </html>
  );
}
