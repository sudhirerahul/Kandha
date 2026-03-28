#!/usr/bin/env node
// scripts/env.mjs — Kandha env CLI: manage .env files across the monorepo
// Usage: pnpm env <command> [args]
//   init       — copy all .env.example files to their real counterparts
//   set KEY=V  — write a key/value into the correct .env file
//   get KEY    — print the value of a key (masked if secret)
//   list       — print all vars across all apps (secrets masked)
//   validate   — check all required vars are non-empty

import { readFileSync, writeFileSync, existsSync, copyFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

// ─── File targets ────────────────────────────────────────────────────────────

const FILES = {
  api: {
    example: resolve(ROOT, "apps/api/.env.example"),
    target: resolve(ROOT, "apps/api/.env"),
    label: "apps/api/.env",
  },
  web: {
    example: resolve(ROOT, "apps/web/.env.example"),
    target: resolve(ROOT, "apps/web/.env.local"),
    label: "apps/web/.env.local",
  },
};

// ─── Ownership map: which file owns each key ─────────────────────────────────

const OWNERSHIP = {
  // API
  GMI_API_KEY: "api",
  GMI_BASE_URL: "api",
  GMI_MODEL: "api",
  DIFY_API_KEY: "api",
  DIFY_BASE_URL: "api",
  DIFY_WORKFLOW_ID_ANALYZE: "api",
  DIFY_WORKFLOW_ID_MIGRATE: "api",
  HYDRA_API_KEY: "api",
  HYDRA_BASE_URL: "api",
  PHOTON_API_KEY: "api",
  DATABASE_URL: "api",
  REDIS_URL: "api",
  MINIO_ENDPOINT: "api",
  MINIO_ACCESS_KEY: "api",
  MINIO_SECRET_KEY: "api",
  MINIO_BUCKET: "api",
  MINIO_SECURE: "api",
  SECRET_KEY: "api",
  LOG_LEVEL: "api",
  // Web
  NEXT_PUBLIC_API_URL: "web",
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: "web",
  CLERK_SECRET_KEY: "web",
};

// Keys that should be masked when printed
const SECRET_KEYS = new Set([
  "GMI_API_KEY",
  "DIFY_API_KEY",
  "HYDRA_API_KEY",
  "PHOTON_API_KEY",
  "MINIO_SECRET_KEY",
  "SECRET_KEY",
  "CLERK_SECRET_KEY",
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "DATABASE_URL",
]);

// Keys that must be non-empty to pass validate
const REQUIRED_KEYS = new Set([
  "GMI_API_KEY",
  "DIFY_API_KEY",
  "DATABASE_URL",
  "REDIS_URL",
  "SECRET_KEY",
  "NEXT_PUBLIC_API_URL",
  "CLERK_SECRET_KEY",
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
]);

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Parse a .env file into a Map, preserving comments and blank lines as-is. */
function parseEnv(filePath) {
  if (!existsSync(filePath)) return new Map();
  const lines = readFileSync(filePath, "utf8").split("\n");
  const map = new Map();
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    map.set(key, value);
  }
  return map;
}

/** Write key=value pairs back to a .env file, merging with existing content. */
function writeEnv(filePath, updates) {
  if (!existsSync(filePath)) {
    writeFileSync(filePath, "", "utf8");
  }
  const lines = readFileSync(filePath, "utf8").split("\n");
  const written = new Set();
  const result = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return line;
    const idx = line.indexOf("=");
    if (idx === -1) return line;
    const key = line.slice(0, idx).trim();
    if (updates.has(key)) {
      written.add(key);
      return `${key}=${updates.get(key)}`;
    }
    return line;
  });
  // Append any new keys not already in the file
  for (const [key, value] of updates) {
    if (!written.has(key)) {
      result.push(`${key}=${value}`);
    }
  }
  writeFileSync(filePath, result.join("\n"), "utf8");
}

function mask(value) {
  if (!value) return "(empty)";
  if (value.length <= 6) return "***";
  return value.slice(0, 4) + "****" + value.slice(-2);
}

function color(code, text) {
  return `\x1b[${code}m${text}\x1b[0m`;
}
const green = (t) => color("32", t);
const red = (t) => color("31", t);
const yellow = (t) => color("33", t);
const cyan = (t) => color("36", t);
const bold = (t) => color("1", t);
const dim = (t) => color("2", t);

// ─── Commands ─────────────────────────────────────────────────────────────────

function cmdInit() {
  let anyCreated = false;
  for (const [app, { example, target, label }] of Object.entries(FILES)) {
    if (!existsSync(example)) {
      console.log(yellow(`  skip  ${label} (no .env.example found)`));
      continue;
    }
    if (existsSync(target)) {
      console.log(dim(`  exists ${label}`));
    } else {
      copyFileSync(example, target);
      console.log(green(`  created ${label}`));
      anyCreated = true;
    }
  }
  if (anyCreated) {
    console.log("\n" + yellow("Fill in the empty values, then run: pnpm env validate"));
  } else {
    console.log("\n" + dim("All .env files already exist."));
  }
}

function cmdSet(args) {
  const pairs = args.map((a) => {
    const idx = a.indexOf("=");
    if (idx === -1) throw new Error(`Invalid format: "${a}" — expected KEY=VALUE`);
    return [a.slice(0, idx).trim(), a.slice(idx + 1).trim()];
  });

  // Group by target file
  const byFile = new Map();
  for (const [key, value] of pairs) {
    const app = OWNERSHIP[key];
    if (!app) throw new Error(`Unknown key: "${key}" — add it to OWNERSHIP in scripts/env.mjs`);
    if (!byFile.has(app)) byFile.set(app, new Map());
    byFile.get(app).set(key, value);
  }

  for (const [app, updates] of byFile) {
    const { target, label } = FILES[app];
    if (!existsSync(target)) {
      throw new Error(`${label} does not exist. Run: pnpm env init`);
    }
    writeEnv(target, updates);
    for (const [k, v] of updates) {
      const display = SECRET_KEYS.has(k) ? mask(v) : v;
      console.log(green(`  set  ${k}=${display}`) + dim(`  → ${label}`));
    }
  }
}

function cmdGet(key) {
  if (!key) throw new Error("Usage: pnpm env get KEY");
  const app = OWNERSHIP[key];
  if (!app) throw new Error(`Unknown key: "${key}"`);
  const { target, label } = FILES[app];
  const map = parseEnv(target);
  const value = map.get(key);
  if (value === undefined) {
    console.log(yellow(`  ${key} is not set in ${label}`));
  } else {
    const display = SECRET_KEYS.has(key) ? mask(value) : value || dim("(empty)");
    console.log(`  ${bold(key)} = ${display}` + dim(`  [${label}]`));
  }
}

function cmdList() {
  for (const [app, { target, label }] of Object.entries(FILES)) {
    console.log("\n" + bold(cyan(`── ${label}`)));
    if (!existsSync(target)) {
      console.log(red(`  (file not found — run: pnpm env init)`));
      continue;
    }
    const map = parseEnv(target);
    if (map.size === 0) {
      console.log(dim("  (empty)"));
      continue;
    }
    for (const [key, value] of map) {
      const display = SECRET_KEYS.has(key)
        ? value ? mask(value) : red("(empty)")
        : value || red("(empty)");
      console.log(`  ${key.padEnd(38)} ${display}`);
    }
  }
  console.log("");
}

function cmdValidate() {
  let errors = 0;
  let checked = 0;
  for (const [app, { target, label }] of Object.entries(FILES)) {
    const map = parseEnv(target);
    for (const key of REQUIRED_KEYS) {
      if (OWNERSHIP[key] !== app) continue;
      checked++;
      const value = map.get(key);
      if (!value || value.trim() === "") {
        console.log(red(`  MISSING  ${key}`) + dim(`  [${label}]`));
        errors++;
      } else {
        console.log(green(`  ok       ${key}`) + dim(`  [${label}]`));
      }
    }
  }
  console.log("");
  if (errors > 0) {
    console.log(red(bold(`✖ ${errors} required variable(s) missing out of ${checked} checked.`)));
    process.exit(1);
  } else {
    console.log(green(bold(`✔ All ${checked} required variables are set.`)));
  }
}

// ─── Router ──────────────────────────────────────────────────────────────────

const [cmd, ...args] = process.argv.slice(2);

const HELP = `
${bold("kandha env")} — manage .env files across the monorepo

${cyan("Commands:")}
  ${green("init")}              Copy all .env.example files to their real counterparts
  ${green("set")} KEY=VALUE     Write one or more values to the correct .env file
  ${green("get")} KEY           Print a single variable (secrets are masked)
  ${green("list")}              Print all variables across all apps (secrets masked)
  ${green("validate")}          Check all required variables are non-empty

${cyan("Examples:")}
  pnpm env init
  pnpm env set GMI_API_KEY=sk-xxx DIFY_API_KEY=dify-xxx
  pnpm env get DATABASE_URL
  pnpm env list
  pnpm env validate
`;

try {
  switch (cmd) {
    case "init":
      cmdInit();
      break;
    case "set":
      if (!args.length) throw new Error("Usage: pnpm env set KEY=VALUE [KEY=VALUE ...]");
      cmdSet(args);
      break;
    case "get":
      cmdGet(args[0]);
      break;
    case "list":
      cmdList();
      break;
    case "validate":
      cmdValidate();
      break;
    default:
      console.log(HELP);
      if (cmd && cmd !== "--help" && cmd !== "-h") {
        console.error(red(`Unknown command: "${cmd}"\n`));
        process.exit(1);
      }
  }
} catch (err) {
  console.error(red(`\nError: ${err.message}\n`));
  process.exit(1);
}
