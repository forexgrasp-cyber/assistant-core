/** @type {import('next').NextConfig} */
const API_BACKEND = process.env.API_BACKEND_URL || "http://localhost:47319";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BACKEND}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
