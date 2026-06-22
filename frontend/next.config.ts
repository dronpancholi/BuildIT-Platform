import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["*.trycloudflare.com", "7dc1-183-82-199-148.ngrok-free.app"],
};

export default nextConfig;
