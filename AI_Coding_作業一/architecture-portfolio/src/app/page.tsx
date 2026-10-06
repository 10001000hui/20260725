"use client";

import Image from "next/image";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

const projects = [
  { id: "courtyard", title: "在城市裡，留一座院子", subtitle: "街角共享住宅", category: "建築設計", year: "2026", image: "courtyard", description: "以共享中庭串連居住與公共空間，練習在緊密的城市紋理中保留光、風與相遇的機會。", process: "從基地觀察、動線草圖到量體推敲，思考住戶與街坊如何共用一個友善的入口。", tools: "基地分析 · 空間配置 · 量體研究" },
  { id: "library", title: "閱讀，從一束光開始", subtitle: "社區閱讀空間", category: "建築設計", year: "2026", image: "library", description: "透過錯落量體與開口方向，探索自然光如何形塑不同的閱讀角落。", process: "比較採光、視線與座位配置，讓安靜閱讀與交流活動各自找到適合的位置。", tools: "日照觀察 · 平面規劃 · 空間敘事" },
  { id: "model", title: "把想像，放到手上", subtitle: "紙板空間模型", category: "模型製作", year: "2026", image: "model", description: "用紙板與簡單材料，將平面上的想法轉譯成能從各個角度觀察的空間。", process: "以切割、拼接與拍攝光影的方式，反覆比較量體比例與入口尺度。", tools: "紙板 · 比例模型 · 光影紀錄" },
  { id: "bim", title: "讓每一道牆，都有邏輯", subtitle: "BIM 建模練習", category: "BIM", year: "2026", image: "bim", description: "從樓層、牆體到開口，練習建立具有構造邏輯與一致資訊的建築模型。", process: "將模型與平面、立面互相對照，觀察修改一個構件時，圖面如何同步更新。", tools: "Revit · 模型資訊 · 圖面整合" },
  { id: "perspective", title: "用一條線，走進空間", subtitle: "透視與表現練習", category: "透視表現", year: "2026", image: "perspective", description: "練習視平線、消失點與人物比例，讓圖面傳達可以被理解的空間感。", process: "從線稿到陰影層次，嘗試以少量線條表現深度、材質與空間氛圍。", tools: "透視草圖 · 線稿 · 空間表現" },
  { id: "print", title: "從螢幕，到真實尺度", subtitle: "3D 列印量體研究", category: "模型製作", year: "2026", image: "print", description: "探索數位建模與實體製作的關係，理解壁厚、支撐與列印方向的限制。", process: "以簡單量體比較不同方向與尺度，記錄數位模型轉為實體時需要調整的細節。", tools: "3D 建模 · 切片規劃 · 製作研究" },
];
const categories = ["全部作品", "建築設計", "模型製作", "BIM", "透視表現", "我的收藏"];
const resources = [
  { number: "01", title: "BIM 與數位建模", description: "從模型邏輯開始，學習讓設計與圖面一起成長。", label: "Autodesk 學習資源", url: "https://www.autodesk.com/learn" },
  { number: "02", title: "3D 製作與列印", description: "認識切片、材料與製作限制，把數位想法帶到桌上。", label: "UltiMaker 學習資源", url: "https://ultimaker.com/learn/" },
  { number: "03", title: "建築學習與職涯", description: "整理你的參考影片；考試資格與抵免制度請以官方公告為準。", label: "開啟參考影片", url: "https://www.youtube.com/watch?v=OvYpRS41nN8" },
];
const storageKey = "architecture-studio-favorites";
function getFavorites() {
  try { return localStorage.getItem(storageKey) || "[]"; } catch { return "[]"; }
}
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("favorites-change", callback);
  return () => { window.removeEventListener("storage", callback); window.removeEventListener("favorites-change", callback); };
}

export default function Home() {
  const [category, setCategory] = useState("全部作品");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<(typeof projects)[number] | null>(null);
  const [notice, setNotice] = useState("");
  const modal = useRef<HTMLDialogElement>(null);
  const rawFavorites = useSyncExternalStore(subscribe, getFavorites, () => "[]");
  let favorites: string[] = [];
  try { const parsed = JSON.parse(rawFavorites); if (Array.isArray(parsed)) favorites = parsed.filter((v): v is string => typeof v === "string"); } catch { /* Ignore damaged browser storage. */ }
  const filtered = projects.filter(p => (category === "全部作品" || (category === "我的收藏" ? favorites.includes(p.id) : p.category === category)) && `${p.title} ${p.subtitle} ${p.tools}`.toLowerCase().includes(query.trim().toLowerCase()));

  useEffect(() => {
    if (selected) {
      modal.current?.showModal();
      const previous = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = previous; };
    }
  }, [selected]);
  function closeModal() { modal.current?.close(); setSelected(null); }
  function toggleFavorite(id: string) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(favorites.includes(id) ? favorites.filter(f => f !== id) : [...favorites, id]));
      window.dispatchEvent(new Event("favorites-change"));
      setNotice("");
    } catch { setNotice("瀏覽器目前無法儲存收藏，仍可正常瀏覽作品。"); }
  }

  return (
    <>
      <a className="skip-link" href="#main">跳至主要內容</a>
      <header className="header"><a href="#" className="brand"><span className="brand-mark">S.</span><span>築跡<span className="brand-en">STUDIO NOTES</span></span></a><nav aria-label="主要導覽"><a href="#works">作品集</a><a href="#learning">學習紀錄</a><a href="#about">關於本站 <span>↗</span></a></nav></header>
      <main id="main">
        <section className="hero container">
          <div className="hero-copy"><p className="eyebrow"><span className="dot" /> ARCHITECTURE & EVERYDAY EXPLORATIONS</p><h1>在空間裡思考，<br />在日常裡<span>築跡。</span></h1><p className="hero-description">一個建築學生的作品與學習筆記。<br />從草圖、模型到數位建構，記錄每一次把想法變成空間的過程。</p><a className="button primary" href="#works">走進我的作品 <span>↗</span></a><a className="text-link" href="#learning">看看我正在學什麼 <span>→</span></a><div className="hero-footnote"><span>DESIGN. MAKE. REFLECT.</span><span>持續學習，持續記錄</span></div></div>
          <figure className="hero-art"><Image src="/images/courtyard.svg" alt="以共享中庭為概念的建築量體原創示意圖" width={960} height={680} priority /><figcaption><span>01 / 空間與日常</span><span>CONCEPT STUDY — 2026</span></figcaption><span className="image-note">從一個想法，到一個空間。</span></figure>
        </section>
        <section id="works" className="works container">
          <div className="section-heading"><div><p className="eyebrow accent">01 — SELECTED WORKS</p><h2>每個作品，都是一次探索。</h2></div><p>在設計與製作之間，<br />找到自己的觀察方式。</p></div>
          <p className="sample-note">本頁為課程示範作品集；作品文字與圖像為示範內容，可替換成你的實際作品。</p>
          <div className="filters"><div className="category-list" aria-label="作品分類">{categories.map(c => <button key={c} aria-pressed={category === c} onClick={() => setCategory(c)} className={category === c ? "filter active" : "filter"}>{c}{c === "我的收藏" && <span> {favorites.length}</span>}</button>)}</div><label className="search"><span aria-hidden="true">⌕</span><input aria-label="搜尋作品" value={query} onChange={e => setQuery(e.target.value)} placeholder="搜尋作品或關鍵字" /></label></div>
          <p className="result-count" role="status" aria-live="polite">共 {filtered.length} 件作品{notice && ` · ${notice}`}</p>
          <div className="project-grid">{filtered.map(p => <article className="project-card" key={p.id}><button className="project-image" onClick={() => setSelected(p)} aria-label={`查看${p.subtitle}詳細介紹`}><Image src={`/images/${p.image}.svg`} alt={`${p.subtitle}的建築概念示意圖`} width={960} height={680} /><span className="view-project">查看作品 ↗</span></button><div className="card-meta"><span>{p.category}</span><span>{p.year}</span></div><div className="card-title"><button onClick={() => setSelected(p)}><h3>{p.title}</h3></button><button className="bookmark" aria-label={`${favorites.includes(p.id) ? "取消收藏" : "收藏"}${p.subtitle}`} aria-pressed={favorites.includes(p.id)} onClick={() => toggleFavorite(p.id)}>{favorites.includes(p.id) ? "★" : "☆"}</button></div><p>{p.subtitle}</p></article>)}</div>
          {filtered.length === 0 && <div className="empty"><h3>這裡還沒有作品</h3><p>{category === "我的收藏" ? "點擊作品旁的星號，把喜歡的探索留在這裡。" : "試試其他關鍵字，或回到全部作品。"}</p><button className="button secondary" onClick={() => { setQuery(""); setCategory("全部作品"); }}>查看全部作品 →</button></div>}
        </section>
        <section id="learning" className="learning"><div className="container"><div className="section-heading"><div><p className="eyebrow accent">02 — LEARNING JOURNAL</p><h2>作品之外，學習也在發生。</h2></div><p>把值得留下的靈感，<br />整理成下一次出發的養分。</p></div><div className="resource-grid">{resources.map(r => <a className="resource" href={r.url} target="_blank" rel="noopener noreferrer" key={r.number}><div className="resource-top"><span>{r.number}</span><span>↗</span></div><h3>{r.title}</h3><p>{r.description}</p><span className="resource-link">{r.label} <span className="sr-only">（開啟新分頁）</span>→</span></a>)}</div><p className="resource-note">延伸閱讀：<a href="https://www.moex.gov.tw/" target="_blank" rel="noopener noreferrer">考選部官方資訊 ↗</a> · 外部學習資源可能更新，考試制度請核對當年度公告。</p></div></section>
        <section id="about" className="about container"><div><p className="eyebrow accent">03 — ABOUT THIS SPACE</p><h2>還在學習，<br />也正在成為。</h2></div><div><p className="about-lead">建築不只是圖面上的線條，<br />也是對生活、環境與人的持續提問。</p><p>「築跡」是一個以建築學生為主題的數位作品集。我們把設計練習、模型製作、BIM 與透視表現放在一起，讓零散的學習累積成能回頭觀看的軌跡。</p><p className="about-small">這是 AI Coding 課程作業的前端網站，無需登入即可瀏覽。收藏只保存在你的瀏覽器，不會上傳個人資料。</p><a className="text-link" href="#works">回到作品，繼續探索 →</a></div></section>
      </main>
      <footer className="footer container"><span className="footer-brand">築跡 / STUDIO NOTES</span><span>建築學生作品與學習紀錄</span><a href="#">回到頂端 ↑</a></footer>
      <dialog ref={modal} className="project-modal" onCancel={() => setSelected(null)} onClose={() => setSelected(null)} onClick={e => { if (e.target === e.currentTarget) closeModal(); }} aria-labelledby="modal-title">{selected && <><button className="modal-close" onClick={closeModal} aria-label="關閉作品介紹">×</button><Image src={`/images/${selected.image}.svg`} alt={`${selected.subtitle}概念示意圖`} width={960} height={680} /><div className="modal-content"><p className="eyebrow accent">{selected.category} / {selected.year} / 示範作品</p><h2 id="modal-title">{selected.title}</h2><p className="modal-subtitle">{selected.subtitle}</p><p>{selected.description}</p><h3>設計與學習過程</h3><p>{selected.process}</p><p className="tools">{selected.tools}</p><button className="button primary" aria-pressed={favorites.includes(selected.id)} onClick={() => toggleFavorite(selected.id)}>{favorites.includes(selected.id) ? "★ 已收藏・點擊取消" : "☆ 收藏這個作品"}</button><p className="storage-note">收藏僅儲存在這個瀏覽器。{notice}</p></div></>}</dialog>
    </>
  );
}
