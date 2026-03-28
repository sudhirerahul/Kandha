// Next.js configuration for the Kandha web application
/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@kandha/ui", "@kandha/types"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.clerk.com",
      },
    ],
  },
};

export default nextConfig;
