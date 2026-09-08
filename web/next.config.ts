import type { NextConfig } from "next";
import path from "node:path";

// Vercel builds from the `web/` root and traces files itself. The Docker image is the only build that
// wants a standalone server bundle and a Turbopack root above `web/` (the repo has a second lockfile).
const docker = process.env.NEXT_OUTPUT === "standalone";

const nextConfig: NextConfig = {
  ...(docker ? { output: "standalone", turbopack: { root: path.join(__dirname, "..") } } : {}),
};

export default nextConfig;
