"use client";

import { motion } from "framer-motion";
import {
  Sparkles,
  Captions,
  Scissors,
  Smartphone,
  BarChart3,
  Zap,
} from "lucide-react";

const features = [
  {
    icon: Sparkles,
    title: "AI Virality Detection",
    description:
      "Our LLM analyzes every moment, scoring for hook strength, curiosity, and standalone power to find what will actually go viral.",
  },
  {
    icon: Scissors,
    title: "Hook-First Editing",
    description:
      "Brevio detects the most attention-grabbing sentence and automatically reorders it to play first — the way viral clips are built.",
  },
  {
    icon: Captions,
    title: "Auto-Burned Captions",
    description:
      "Animated subtitles are generated and burned directly into your clips. Customize font, size, and style to match your brand.",
  },
  {
    icon: Smartphone,
    title: "Vertical 9:16 Reframe",
    description:
      "One toggle converts landscape footage into portrait-ready Shorts, Reels, and TikToks with intelligent blurred-fill framing.",
  },
  {
    icon: BarChart3,
    title: "Virality Scoring",
    description:
      "Every clip gets a detailed breakdown: virality score, hook strength, curiosity factor, and a plain-English reason for why it works.",
  },
  {
    icon: Zap,
    title: "Production Polish",
    description:
      "Fade transitions, EBU-standard loudness normalization, and animated progress bars — clips come out broadcast-ready.",
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

export function Features() {
  return (
    <section id="features" className="relative py-28 sm:py-36">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent" />

      <div className="relative mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">
            Features
          </p>
          <h2 className="mt-3 text-3xl font-bold sm:text-4xl lg:text-5xl">
            Everything You Need to{" "}
            <span className="font-accent text-gradient">Go Viral</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground sm:text-lg">
            From raw footage to polished, platform-ready clips in minutes. No
            editing skills required.
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              className="group relative overflow-hidden rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5"
            >
              <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-primary/5 transition-transform duration-500 group-hover:scale-150" />
              <div className="relative">
                <div className="mb-4 flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                  <feature.icon className="size-5" />
                </div>
                <h3 className="text-base font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
