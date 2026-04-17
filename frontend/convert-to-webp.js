/**
 * convert-to-webp.js
 *
 * Converts PNG / JPG / JPEG images in ./public to WebP.
 * Originals are left untouched.
 *
 * Usage:
 *   node convert-to-webp.js              ← converts every PNG/JPG in /public
 *   node convert-to-webp.js archi1.png   ← converts a single file
 *
 * Options (edit below):
 *   QUALITY   1-100  higher = better quality / larger file  (default 82)
 *   EFFORT    0-6    higher = slower encode / smaller file   (default 4)
 */

const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

// ── config ────────────────────────────────────────────────────────────────────
const PUBLIC_DIR = path.join(__dirname, "public");
const QUALITY = 82;
const EFFORT = 4;
const EXTENSIONS = [".png", ".jpg", ".jpeg"];
// ─────────────────────────────────────────────────────────────────────────────

function formatKB(bytes) {
  return (bytes / 1024).toFixed(0) + " KB";
}

async function convertFile(inputPath) {
  const ext = path.extname(inputPath).toLowerCase();
  if (!EXTENSIONS.includes(ext)) return;

  const outputPath = inputPath.replace(/\.(png|jpe?g)$/i, ".webp");

  if (outputPath === inputPath) return; // already webp

  const inputSize = fs.statSync(inputPath).size;

  await sharp(inputPath)
    .webp({ quality: QUALITY, effort: EFFORT })
    .toFile(outputPath);

  const outputSize = fs.statSync(outputPath).size;
  const saving = (((inputSize - outputSize) / inputSize) * 100).toFixed(1);

  console.log(
    `✓  ${path.basename(inputPath).padEnd(24)}` +
      `${formatKB(inputSize).padStart(10)}  →  ` +
      `${formatKB(outputSize).padStart(10)}  (${saving}% smaller)`
  );
}

async function main() {
  const arg = process.argv[2]; // optional: single filename

  let files;

  if (arg) {
    // single file passed on CLI
    const target = path.resolve(PUBLIC_DIR, arg);
    if (!fs.existsSync(target)) {
      console.error(`File not found: ${target}`);
      process.exit(1);
    }
    files = [target];
  } else {
    // scan entire public/ directory
    files = fs
      .readdirSync(PUBLIC_DIR)
      .filter((f) => EXTENSIONS.includes(path.extname(f).toLowerCase()))
      .map((f) => path.join(PUBLIC_DIR, f));
  }

  if (files.length === 0) {
    console.log("No PNG / JPG files found in public/.");
    return;
  }

  console.log(`\nConverting ${files.length} file(s) → WebP  (quality ${QUALITY}, effort ${EFFORT})\n`);
  console.log("  File                       Original      WebP");
  console.log("  " + "─".repeat(54));

  for (const file of files) {
    await convertFile(file);
  }

  console.log("\nDone. Originals untouched.\n");
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
