import { cpSync, existsSync } from "node:fs";
import { spawn } from "node:child_process";
if (!existsSync(".next/standalone/server.js"))
  throw new Error("Run npm run build before starting.");
cpSync(".next/static", ".next/standalone/.next/static", { recursive: true });
cpSync("public", ".next/standalone/public", { recursive: true });
const child = spawn(process.execPath, [".next/standalone/server.js"], {
  stdio: "inherit",
  env: {
    ...process.env,
    HOSTNAME: "127.0.0.1",
    PORT: process.env.PORT || "3000",
  },
});
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => child.kill(signal));
child.on("exit", (code) => process.exit(code ?? 0));
