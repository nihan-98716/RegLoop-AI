import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the Docker multi-stage build (copies only production files).
  output: "standalone",

  // Expose the API base URL to the browser bundle.
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api",
  },
};

export default nextConfig;
