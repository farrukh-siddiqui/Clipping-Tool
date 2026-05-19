"use client";

import { motion } from "framer-motion";
import { Upload, SlidersHorizontal, Download } from "lucide-react";

const steps = [
  {
    icon: Upload,
    step: "01",
    title: "Upload Your Video",
    description:
      "Drop any long-form video — a podcast episode, interview, stream, or lecture. Brevio handles files of any length.",
  },
  {
    icon: SlidersHorizontal,
    step: "02",
    title: "Configure & Launch",
    description:
      "Choose how many clips you want, set the target duration, toggle captions and vertical mode. Hit go and let AI do the work.",
  },
  {
    icon: Download,
    step: "03",
    title: "Download Viral Clips",
    description:
      "Review AI-ranked clips with virality scores, hook highlights, and full transcripts. Download and publish instantly.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative py-28 sm:py-36">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">
            How It Works
          </p>
          <h2 className="mt-3 text-3xl font-bold sm:text-4xl lg:text-5xl">
            Three Steps to{" "}
            <span className="font-accent text-gradient">Viral Content</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground sm:text-lg">
            What used to take hours of scrubbing through footage now happens in
            minutes.
          </p>
        </motion.div>

        <div className="relative mt-20">
          {/* Connector line */}
          <div className="absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-border to-transparent lg:block" />

          <div className="flex flex-col gap-16 lg:gap-24">
            {steps.map((step, i) => (
              <motion.div
                key={step.step}
                initial={{ opacity: 0, x: i % 2 === 0 ? -40 : 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className={`flex flex-col items-center gap-8 lg:flex-row ${
                  i % 2 !== 0 ? "lg:flex-row-reverse" : ""
                }`}
              >
                <div className="flex-1 text-center lg:text-left">
                  <div className="inline-flex items-center gap-3">
                    <span className="text-sm font-bold text-primary">
                      {step.step}
                    </span>
                    <div className="h-px w-8 bg-primary/30" />
                  </div>
                  <h3 className="mt-3 text-2xl font-bold sm:text-3xl">
                    {step.title}
                  </h3>
                  <p className="mt-3 max-w-md text-muted-foreground">
                    {step.description}
                  </p>
                </div>

                {/* Center node */}
                <div className="relative z-10 flex size-16 shrink-0 items-center justify-center rounded-2xl border border-border bg-card shadow-lg glow">
                  <step.icon className="size-7 text-primary" />
                </div>

                <div className="flex-1" />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
