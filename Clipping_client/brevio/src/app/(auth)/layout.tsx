import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-6 py-12">
      {/* Background effects */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-40 left-1/4 h-[500px] w-[500px] rounded-full bg-[oklch(0.56_0.22_260_/_0.05)] blur-[120px] dark:bg-[oklch(0.62_0.24_260_/_0.08)]" />
        <div className="absolute -bottom-40 right-1/4 h-[400px] w-[400px] rounded-full bg-[oklch(0.58_0.18_220_/_0.05)] blur-[100px] dark:bg-[oklch(0.66_0.20_220_/_0.08)]" />
      </div>

      <Link
        href="/"
        className="relative z-10 mb-8 flex items-center gap-2.5"
      >
        <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-brand">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            className="size-5 text-white"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        </div>
        <span
          className="text-xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-heading), sans-serif" }}
        >
          Brevio
        </span>
      </Link>

      <div className="relative z-10 w-full max-w-md">{children}</div>

      <p className="relative z-10 mt-8 text-center text-xs text-muted-foreground">
        &copy; {new Date().getFullYear()} Brevio. All rights reserved.
      </p>
    </div>
  );
}
