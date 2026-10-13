"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Brand from "@/components/shared/Brand";
import HeroVideo from "./HeroVideo";
import CursorLight from "@/components/shared/CursorLight";
import Icon from "@/components/shared/Icon";
import { api } from "@/lib/api";
const nav = [
  ["Explore Demo", "/demo"],
  ["How It Works", "/how-it-works"],
  ["FAQs", "/faq"],
  ["My Projects", "/app"],
];
const delay = (s: number) => ({ "--d": `${s}s` }) as React.CSSProperties;
export default function Landing() {
  const [open, setOpen] = useState(false),
    [signed, setSigned] = useState(false);
  const burger = useRef<HTMLButtonElement>(null),
    menu = useRef<HTMLElement>(null),
    main = useRef<HTMLElement>(null),
    footer = useRef<HTMLElement>(null);
  useEffect(() => {
    document.documentElement.classList.add("landing-route");
    api("/auth/me")
      .then(() => setSigned(true))
      .catch(() => {});
    const nodes = [...document.querySelectorAll<HTMLElement>(".appear")];
    const end = (e: Event) => {
      if (e.target === e.currentTarget)
        (e.currentTarget as HTMLElement).classList.add("is-in");
    };
    nodes.forEach((n) => {
      n.addEventListener("animationend", end);
      n.addEventListener("animationcancel", end);
    });
    let frame2 = 0;
    const frame = requestAnimationFrame(() => {
      frame2 = requestAnimationFrame(() => {
        if (
          matchMedia("(prefers-reduced-motion: reduce)").matches ||
          !nodes.some((n) =>
            n
              .getAnimations?.()
              .some(
                (a) => a.playState === "running" || a.playState === "finished",
              ),
          )
        )
          nodes.forEach((n) => n.classList.add("is-in"));
      });
    });
    return () => {
      document.documentElement.classList.remove("landing-route");
      document.body.classList.remove("menu-open");
      cancelAnimationFrame(frame);
      cancelAnimationFrame(frame2);
      nodes.forEach((n) => {
        n.removeEventListener("animationend", end);
        n.removeEventListener("animationcancel", end);
      });
    };
  }, []);
  useEffect(() => {
    document.body.classList.toggle("menu-open", open);
    if (main.current) main.current.inert = open;
    if (footer.current) footer.current.inert = open;
    if (open) menu.current?.querySelector<HTMLAnchorElement>("a")?.focus();
    const close = () => {
      setOpen(false);
      burger.current?.focus();
    };
    const key = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const items = [
          burger.current,
          ...Array.from(
            menu.current?.querySelectorAll<HTMLAnchorElement>("a") || [],
          ),
        ].filter(Boolean) as HTMLElement[];
        const i = items.indexOf(document.activeElement as HTMLElement);
        e.preventDefault();
        items[
          (i + (e.shiftKey ? -1 : 1) + items.length) % items.length
        ]?.focus();
      }
    };
    const resize = () => {
      if (innerWidth >= 901) setOpen(false);
    };
    document.addEventListener("keydown", key);
    window.addEventListener("resize", resize);
    return () => {
      document.removeEventListener("keydown", key);
      window.removeEventListener("resize", resize);
    };
  }, [open]);
  return (
    <>
      <CursorLight />
      <div className="grain" aria-hidden="true" />
      <div className="hero-photo" aria-hidden="true" />
      <div className={`page ${open ? "menu-is-open" : ""}`}>
        <div
          className="menu-backdrop"
          onClick={() => {
            setOpen(false);
            burger.current?.focus();
          }}
        />
        <header className="site-header">
          <div className="appear scale logo-wrap" style={delay(0.08)}>
            <Brand />
          </div>
          <nav ref={menu} id="site-nav" aria-label="Primary">
            {nav.map(([label, href], i) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={`nav-pill appear ${i % 2 ? "soft" : "scale"}`}
                style={delay(0.16 + i * 0.12)}
              >
                {label}
              </Link>
            ))}
          </nav>
          <Link
            href={signed ? "/app" : "/register"}
            className="button solid header-cta appear scale"
            style={delay(0.34)}
          >
            {signed ? "Open Workspace" : "Get Started"}
          </Link>
          <button
            ref={burger}
            className="burger appear scale"
            style={delay(0.34)}
            aria-controls="site-nav"
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen(!open)}
          >
            <span />
            <span />
            <span />
          </button>
        </header>
        <main ref={main} className="hero" id="top">
          <HeroVideo />
          <div className="hero-copy">
            <div className="badge appear pop" style={delay(0.22)}>
              <svg
                className="sparkle"
                width="18"
                height="20"
                viewBox="0 0 24 24"
                fill="white"
                aria-hidden="true"
              >
                <path d="M12 2.6C12.55 2.6 12.88 3.15 13.08 4.7c.62 4.7 1.52 5.6 6.22 6.22 1.55.2 2.1.53 2.1 1.08s-.55.88-2.1 1.08c-4.7.62-5.6 1.52-6.22 6.22-.2 1.55-.53 2.1-1.08 2.1s-.88-.55-1.08-2.1c-.62-4.7-1.52-5.6-6.22-6.22C3.15 12.88 2.6 12.55 2.6 12s.55-.88 2.1-1.08c4.7-.62 5.6-1.52 6.22-6.22C11.12 3.15 11.45 2.6 12 2.6Z" />
              </svg>
              AI Codebase Understanding
            </div>
            <h1>
              <span className="line-mask">
                <span className="appear mask" style={delay(0.42)}>
                  Understand your <em>codebase</em>.
                </span>
              </span>
              <span className="line-mask">
                <span className="appear mask" style={delay(0.62)}>
                  Build with confidence.
                </span>
              </span>
            </h1>
            <p
              className="lede appear soft"
              style={{ ...delay(0.82), animationDuration: "1.25s" }}
            >
              Explore your repository, ask questions, and get clear answers
              backed by real code.
            </p>
            <div className="hero-actions">
              <Link
                href="/app/new"
                className="button solid appear btn-in"
                style={delay(0.96)}
              >
                Analyze Your Code
              </Link>
              <Link
                href="/demo"
                className="button ghost appear side"
                style={delay(1.1)}
              >
                Explore Demo
              </Link>
            </div>
            <p className="creator-credit home-credit">Powered by Malik Ismail Manzoor</p>
          </div>
        </main>
        <footer ref={footer} className="stats">
          <div className="stat appear stat-in" style={delay(1.12)}>
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
              <defs>
                <linearGradient id="pill-left">
                  <stop stopColor="white" stopOpacity=".38" />
                  <stop offset="1" stopColor="#3a3a3a" stopOpacity=".62" />
                </linearGradient>
                <linearGradient id="pill-right">
                  <stop stopColor="#3a3a3a" stopOpacity=".62" />
                  <stop offset="1" stopColor="white" stopOpacity=".38" />
                </linearGradient>
              </defs>
              <rect
                x="3.4"
                y="2.6"
                width="7.2"
                height="18.8"
                rx="3.6"
                fill="url(#pill-left)"
              />
              <rect
                x="13.4"
                y="2.6"
                width="7.2"
                height="18.8"
                rx="3.6"
                fill="url(#pill-right)"
              />
              <rect
                x="9.2"
                y="10.9"
                width="5.6"
                height="2.2"
                rx="1.1"
                fill="#4a4a4a"
              />
            </svg>
            Code-aware search
          </div>
          <div className="stat appear stat-in" style={delay(1.28)}>
            <Icon />
            File &amp; line citations
          </div>
          <div className="stat appear stat-in" style={delay(1.44)}>
            <Icon name="book" />
            Guided onboarding
          </div>
        </footer>
      </div>
    </>
  );
}
