"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./HeroSection.module.css";

interface HeroSectionProps {
  /** Drop in any <img>, <Image />, or other element as your custom visual */
  image?: React.ReactNode;
  headline?: string;
  subheadline?: string;
  ctaPrimaryLabel?: string;
  ctaPrimaryHref?: string;
  ctaSecondaryLabel?: string;
  ctaSecondaryHref?: string;
}

export default function HeroSection({
  image,
  headline = "The wealth advisor for high-stakes financial decisions",
  subheadline = "Institutional-grade insight. Delivered personally.",
  ctaPrimaryLabel = "Get Started",
  ctaPrimaryHref = "#",
  ctaSecondaryLabel = "See Why",
  ctaSecondaryHref = "#",
}: HeroSectionProps) {
  const heroRef = useRef<HTMLElement>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Staggered entrance
    const t = setTimeout(() => setLoaded(true), 60);
    return () => clearTimeout(t);
  }, []);

  // Subtle parallax on the image column
  useEffect(() => {
    const el = heroRef.current;
    if (!el) return;
    const handleMouseMove = (e: MouseEvent) => {
      const { left, top, width, height } = el.getBoundingClientRect();
      const rx = ((e.clientX - left) / width - 0.5) * 12;
      const ry = ((e.clientY - top) / height - 0.5) * -8;
      el.style.setProperty("--rx", `${rx}px`);
      el.style.setProperty("--ry", `${ry}px`);
    };
    el.addEventListener("mousemove", handleMouseMove);
    return () => el.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <section
      ref={heroRef}
      className={`${styles.hero} ${loaded ? styles.heroLoaded : ""}`}
      aria-label="Hero"
    >
      {/* ── Decorative grain overlay ── */}
      <div className={styles.grain} aria-hidden="true" />

      {/* ── Thin rule top accent ── */}
      <div className={styles.topRule} aria-hidden="true" />

      <div className={styles.inner}>
        {/* ────── LEFT: copy ────── */}
        <div className={styles.copy}>
          <p className={styles.eyebrow}>Private Wealth Advisory</p>

          <h1 className={styles.headline}>{headline}</h1>

          <p className={styles.sub}>{subheadline}</p>

          <div className={styles.actions}>
            <a href={ctaPrimaryHref} className={styles.btnPrimary}>
              {ctaPrimaryLabel}
              <span className={styles.arrow}>→</span>
            </a>

            <a href={ctaSecondaryHref} className={styles.btnSecondary}>
              <span className={styles.playIcon} aria-hidden="true">
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                  <path d="M6.5 5.5l8 4.5-8 4.5V5.5z" />
                </svg>
              </span>
              {ctaSecondaryLabel}
            </a>
          </div>

          {/* micro trust strip */}
          <div className={styles.trustStrip}>
            <span>AUM $4.2B+</span>
            <span className={styles.dot}>·</span>
            <span>Est. 1998</span>
            <span className={styles.dot}>·</span>
            <span>Fiduciary Standard</span>
          </div>
        </div>

        {/* ────── RIGHT: image slot ────── */}
        <div className={styles.imageWrap} aria-label="Hero illustration">
          {image ? (
            image
          ) : (
            /* placeholder shown when no image prop is passed */
            <div className={styles.imagePlaceholder}>
              <span>Your Image Here</span>
            </div>
          )}
          {/* floating accent card */}
          <div className={styles.accentCard}>
            <span className={styles.accentLabel}>Portfolio Growth</span>
            <span className={styles.accentValue}>+24.8%</span>
            <span className={styles.accentSub}>YTD · Risk-adjusted</span>
          </div>
        </div>
      </div>

      {/* ── bottom scrolling ticker ── */}
      <div className={styles.ticker} aria-hidden="true">
        <div className={styles.tickerTrack}>
          {[
            "Estate Planning",
            "Tax Optimisation",
            "Private Equity",
            "Family Office",
            "Alternative Assets",
            "Risk Management",
            "Succession Planning",
            "Impact Investing",
          ]
            .concat([
              "Estate Planning",
              "Tax Optimisation",
              "Private Equity",
              "Family Office",
              "Alternative Assets",
              "Risk Management",
              "Succession Planning",
              "Impact Investing",
            ])
            .map((item, i) => (
              <span key={i} className={styles.tickerItem}>
                {item} <span className={styles.tickerDivider}>✦</span>
              </span>
            ))}
        </div>
      </div>
    </section>
  );
}