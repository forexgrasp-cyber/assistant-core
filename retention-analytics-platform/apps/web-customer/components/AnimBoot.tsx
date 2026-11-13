"use client";

import { useEffect } from "react";

/**
 * AnimBoot — injects the generated style_engines assets (anim.css + GSAP CDN +
 * anim.js) into the page head. Mount once on the marketing landing page only;
 * product/dashboard pages never load these.
 */
export default function AnimBoot() {
  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/anim/anim.css";
    document.head.appendChild(link);

    const load = (src: string) =>
      new Promise<void>((resolve) => {
        const s = document.createElement("script");
        s.src = src;
        s.onload = () => resolve();
        s.onerror = () => resolve();
        document.head.appendChild(s);
      });

    (async () => {
      await load("https://unpkg.com/gsap@3.12/dist/gsap.min.js");
      await load("https://unpkg.com/gsap@3.12/dist/ScrollTrigger.min.js");
      await load("/anim/anim.js");
    })();

    return () => {
      if (link.parentNode) link.parentNode.removeChild(link);
    };
  }, []);

  return null;
}
