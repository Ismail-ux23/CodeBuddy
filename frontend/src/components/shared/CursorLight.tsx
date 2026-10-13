"use client";
import { useEffect, useRef } from "react";

export default function CursorLight() {
  const light = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = light.current;
    if (!node) return;
    const preference = matchMedia("(pointer: fine) and (prefers-reduced-motion: no-preference)");
    let frame = 0, x = 0, y = 0, targetX = 0, targetY = 0, visible = false;
    const tick = () => {
      x += (targetX - x) * 0.16;
      y += (targetY - y) * 0.16;
      node.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      if (Math.abs(targetX - x) + Math.abs(targetY - y) > 0.2) frame = requestAnimationFrame(tick);
      else frame = 0;
    };
    const hide = () => { node.style.opacity = "0"; visible = false; cancelAnimationFrame(frame); frame = 0; };
    const move = (event: PointerEvent) => {
      if (!preference.matches || event.pointerType === "touch") return hide();
      targetX = event.clientX; targetY = event.clientY;
      if (!visible) { x = targetX; y = targetY; visible = true; node.style.opacity = "1"; }
      if (!frame) frame = requestAnimationFrame(tick);
    };
    window.addEventListener("pointermove", move, { passive: true });
    document.documentElement.addEventListener("pointerleave", hide);
    window.addEventListener("blur", hide);
    preference.addEventListener("change", hide);
    return () => {
      hide(); window.removeEventListener("pointermove", move);
      document.documentElement.removeEventListener("pointerleave", hide);
      window.removeEventListener("blur", hide); preference.removeEventListener("change", hide);
    };
  }, []);
  return <div ref={light} className="cursor-light" aria-hidden="true"><span /></div>;
}
