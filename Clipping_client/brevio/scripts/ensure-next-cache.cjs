/**
 * Optional: junction .next/cache to %LOCALAPPDATA% (use npm run dev:local-cache).
 * Can cause Turbopack persistence errors on some setups; default `npm run dev` does not use this.
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const projectRoot = path.join(__dirname, "..");
const nextDir = path.join(projectRoot, ".next");
const cacheLink = path.join(nextDir, "cache");
const cacheTarget = path.join(
  process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"),
  "clipping-tool-brevio-cache",
);

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function isLinkedToTarget(linkPath) {
  if (!fs.existsSync(linkPath)) return false;
  try {
    const resolved = fs.realpathSync.native(linkPath);
    const targetResolved = fs.realpathSync.native(cacheTarget);
    return resolved.toLowerCase() === targetResolved.toLowerCase();
  } catch {
    return false;
  }
}

function moveAsideIfRegularDir(dir) {
  if (!fs.existsSync(dir) || isLinkedToTarget(dir)) return;
  const backup = `${dir}.bak`;
  if (fs.existsSync(backup)) {
    console.warn(
      `[dev] ${path.basename(dir)}.bak exists; delete .next/cache or .next/cache.bak if dev is slow.`,
    );
    return;
  }
  fs.renameSync(dir, backup);
  console.log(`[dev] Moved ${path.basename(dir)} to ${path.basename(backup)}`);
}

function createJunction(link, target) {
  execSync(`cmd /c mklink /J "${link}" "${target}"`, { stdio: "inherit" });
  console.log(`[dev] ${link} -> ${target}`);
}

function main() {
  if (process.platform !== "win32") return;

  ensureDir(cacheTarget);
  ensureDir(nextDir);

  if (isLinkedToTarget(cacheLink)) return;

  moveAsideIfRegularDir(cacheLink);

  if (!fs.existsSync(cacheLink)) {
    createJunction(cacheLink, cacheTarget);
  }
}

main();
