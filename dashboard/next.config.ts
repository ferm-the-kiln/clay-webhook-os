import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/campaigns",
        destination: "/outbound/campaigns",
        permanent: true,
      },
      {
        source: "/plays",
        destination: "/analyze/plays",
        permanent: true,
      },
      {
        source: "/skills",
        destination: "/lab",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
