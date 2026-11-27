import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "인사이트 서재",
  description: "업무와 의사결정에 바로 적용하는 개인 AI 디지털 서재",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
