import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "築跡 Studio Notes｜建築學生作品與學習紀錄",
  description: "從建築設計、模型製作到 BIM 與透視表現，探索建築學生的作品與學習軌跡。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-Hant"><body>{children}</body></html>;
}
