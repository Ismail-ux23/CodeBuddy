"use client";

import { useEffect, useRef, useState } from "react";

/** Original local motion asset. No provider requests, audio, or remote video. */
export default function HeroVideo() {
  const video = useRef<HTMLVideoElement>(null);
  const [paused, setPaused] = useState(true);
  const [reduced, setReduced] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => {
      setReduced(preference.matches);
      if (preference.matches) {
        video.current?.pause();
        setPaused(true);
      } else {
        video.current?.play().then(() => setPaused(false)).catch(() => setPaused(true));
      }
    };
    sync();
    preference.addEventListener("change", sync);
    return () => preference.removeEventListener("change", sync);
  }, []);

  async function toggle() {
    if (!video.current) return;
    if (paused) {
      try { await video.current.play(); setPaused(false); } catch { setFailed(true); }
    } else {
      video.current.pause();
      setPaused(true);
    }
  }

  return <>
    <div className="hero-motion" aria-hidden="true">
      <video ref={video} muted loop playsInline preload="auto"
        poster="/video/code-orbit-4k-poster.png"
        onError={() => setFailed(true)}
        className={failed ? "video-failed" : ""}>
        <source src="/video/code-orbit-4k.mp4" type="video/mp4" />
      </video>
    </div>
    {!reduced && !failed && <button className="motion-toggle" onClick={toggle}
      aria-label={paused ? "Play hero animation" : "Pause hero animation"}
      title={paused ? "Play animation" : "Pause animation"}>
      {paused ? <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m5 3 8 5-8 5Z" fill="currentColor" /></svg> : <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3v10M11 3v10" stroke="currentColor" strokeWidth="2" /></svg>}
    </button>}
  </>;
}
