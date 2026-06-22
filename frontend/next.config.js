// next.config.js – force Turbopack to use the correct workspace root
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Explicitly tell Turbopack where the project root is (the directory containing next/package.json)
  // This resolves the "could not find Next.js package" error.
  turbopack: {
    root: __dirname,
  },
  // Optional: suppress noisy Turbopack logs during dev
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.infrastructureLogging = { level: 'warn' };
    }
    return config;
  },
};
module.exports = nextConfig;
