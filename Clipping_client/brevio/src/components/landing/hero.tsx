"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function FloatingOrb({
  className,
  delay = 0,
}: {
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      animate={{
        y: [0, -20, 0],
        scale: [1, 1.05, 1],
      }}
      transition={{
        duration: 6,
        repeat: Infinity,
        ease: "easeInOut",
        delay,
      }}
    />
  );
}

function AnimatedCounter({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.5 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ type: "spring", stiffness: 200, damping: 15 }}
        className="text-2xl font-bold text-gradient sm:text-3xl"
      >
        {value}
      </motion.div>
      <div className="mt-1 text-xs text-muted-foreground sm:text-sm">{label}</div>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden pt-16">
      {/* Background effects */}
      <div className="pointer-events-none absolute inset-0">
        <FloatingOrb
          className="absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-[oklch(0.56_0.22_260_/_0.07)] blur-[120px] dark:bg-[oklch(0.62_0.24_260_/_0.10)]"
          delay={0}
        />
        <FloatingOrb
          className="absolute -bottom-32 right-1/4 h-[400px] w-[400px] rounded-full bg-[oklch(0.58_0.18_220_/_0.06)] blur-[100px] dark:bg-[oklch(0.66_0.20_220_/_0.09)]"
          delay={2}
        />
        <FloatingOrb
          className="absolute top-1/3 right-1/3 h-[300px] w-[300px] rounded-full bg-[oklch(0.60_0.20_300_/_0.04)] blur-[80px] dark:bg-[oklch(0.60_0.22_300_/_0.07)]"
          delay={4}
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,var(--background)_70%)]" />
      </div>

      {/* Grid pattern overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.015] dark:opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(oklch(0.56 0.22 260) 1px, transparent 1px), linear-gradient(90deg, oklch(0.56 0.22 260) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      <div className="relative z-10 mx-auto max-w-6xl px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Badge
            variant="secondary"
            className="mb-6 gap-1.5 border-primary/20 bg-primary/5 px-3.5 py-1.5 text-primary dark:border-primary/30 dark:bg-primary/10"
          >
            <Sparkles className="size-3.5" />
            AI-Powered Clip Extraction
          </Badge>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mx-auto max-w-4xl text-4xl font-bold leading-[1.08] sm:text-5xl md:text-6xl lg:text-7xl"
        >
          Turn Long Videos Into{" "}
          <span className="font-accent text-gradient glow-text">Viral Clips</span>
          <br />
          <span className="text-muted-foreground">Automatically</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg md:text-xl"
        >
          Brevio uses AI to find the most engaging moments in your podcasts,
          interviews, and streams — then delivers polished, caption-ready clips
          optimized for TikTok, Reels, and Shorts.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
        >
          <Button
            size="lg"
            className="h-12 gap-2 bg-gradient-brand px-6 text-base text-white shadow-lg hover:opacity-90 glow"
            render={<Link href="/signup" />}
          >
            Start Clipping Free
            <ArrowRight className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="h-12 gap-2 px-6 text-base"
            render={<Link href="#how-it-works" />}
          >
            <Play className="size-4" />
            See How It Works
          </Button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="mt-16 flex items-center justify-center gap-8 sm:gap-14"
        >
          <AnimatedCounter value="10x" label="Faster Than Manual" />
          <div className="h-8 w-px bg-border" />
          <AnimatedCounter value="92+" label="Avg. Virality Score" />
          <div className="h-8 w-px bg-border" />
          <AnimatedCounter value="9:16" label="Shorts Ready" />
        </motion.div>

        {/* Mockup preview */}
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="relative mx-auto mt-20 max-w-4xl"
        >
          <div className="glow rounded-2xl border border-border bg-card p-2 shadow-2xl">
            <div className="overflow-hidden rounded-xl bg-muted">
              <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
                <div className="flex gap-1.5">
                  <div className="size-3 rounded-full bg-red-400/80" />
                  <div className="size-3 rounded-full bg-yellow-400/80" />
                  <div className="size-3 rounded-full bg-green-400/80" />
                </div>
                <div className="mx-auto rounded-md bg-muted px-4 py-1 text-xs text-muted-foreground">
                  app.brevio.ai/dashboard
                </div>
              </div>
              <div className="relative aspect-video bg-gradient-to-br from-muted to-muted/50 p-6 sm:p-10">
                <div className="grid h-full grid-cols-3 gap-4">
                  {[92, 87, 78].map((score, i) => (
                    <motion.div
                      key={score}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.8 + i * 0.15, duration: 0.5 }}
                      className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 shadow-sm"
                    >
                      <div className="aspect-[9/16] rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                        <Play className="size-6 text-primary/40 sm:size-8" />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                          {score}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          Clip {i + 1}
                        </div>
                      </div>
                      <div className="hidden sm:block">
                        <div className="h-2 w-full rounded-full bg-muted" />
                        <div className="mt-1.5 h-2 w-3/4 rounded-full bg-muted" />
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="pointer-events-none absolute -inset-4 rounded-3xl bg-gradient-to-b from-primary/5 to-transparent blur-2xl" />
        </motion.div>
      </div>
    </section>
  );
}
