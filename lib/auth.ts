import { createHmac, timingSafeEqual } from 'crypto'
import { requireEnv } from './env'

const SESSION_DURATION_MS = 7 * 24 * 60 * 60 * 1000

function sign(payload: string): string {
  const secret = requireEnv('SESSION_SECRET')
  return createHmac('sha256', secret).update(payload).digest('hex')
}

export function createSessionToken(): string {
  const expiresAt = Date.now() + SESSION_DURATION_MS
  const payload = String(expiresAt)
  return `${payload}.${sign(payload)}`
}

export function verifySessionToken(token: string | undefined): boolean {
  if (!token) return false
  const [payload, signature] = token.split('.')
  if (!payload || !signature) return false
  if (!/^\d+$/.test(payload)) return false
  if (Date.now() > Number(payload)) return false

  const expected = sign(payload)
  const a = Buffer.from(signature)
  const b = Buffer.from(expected)
  if (a.length !== b.length) return false
  return timingSafeEqual(a, b)
}

export function verifyPassword(input: string): boolean {
  const expected = requireEnv('ADMIN_PASSWORD')
  if (input.length !== expected.length) return false
  return timingSafeEqual(Buffer.from(input), Buffer.from(expected))
}
