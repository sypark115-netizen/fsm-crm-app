import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 상위 폴더(fsm-crm-app)의 lockfile과 섞이지 않도록 이 폴더를 루트로 고정
  turbopack: { root: __dirname },
};

export default nextConfig;
