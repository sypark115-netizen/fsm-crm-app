const REQUIRED_ENV_VARS = ['NOTION_TOKEN', 'NOTION_DATABASE_ID', 'ADMIN_PASSWORD', 'SESSION_SECRET'] as const

export type RequiredEnvVar = (typeof REQUIRED_ENV_VARS)[number]

export function requireEnv(name: RequiredEnvVar): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`환경변수 ${name}가 설정되지 않았습니다. .env.local을 확인하세요.`)
  }
  return value
}

export function validateEnv(): void {
  for (const name of REQUIRED_ENV_VARS) {
    requireEnv(name)
  }
}
