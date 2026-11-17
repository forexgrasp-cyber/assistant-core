/** @type {import('next').NextConfig} */
const API_BACKEND = process.env.API_BACKEND_URL || "http://localhost:47319";

const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_AUTH_REQUIRED:
      process.env.NEXT_PUBLIC_AUTH_REQUIRED ||
      (process.env.NODE_ENV === "production" ? "true" : "false"),
  },
  async rewrites() {
    return [
      // API surface paths (health, SEO, auth, etc.) proxied to the backend
      { source: "/health", destination: `${API_BACKEND}/health` },
      { source: "/health/:path*", destination: `${API_BACKEND}/health/:path*` },
      { source: "/metrics", destination: `${API_BACKEND}/metrics` },
      { source: "/robots.txt", destination: `${API_BACKEND}/robots.txt` },
      { source: "/sitemap.xml", destination: `${API_BACKEND}/sitemap.xml` },
      { source: "/llms.txt", destination: `${API_BACKEND}/llms.txt` },
      { source: "/docs", destination: `${API_BACKEND}/docs` },
      { source: "/openapi.json", destination: `${API_BACKEND}/openapi.json` },
      { source: "/redoc", destination: `${API_BACKEND}/redoc` },
      // Main API proxy
      { source: "/api/:path*", destination: `${API_BACKEND}/api/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
