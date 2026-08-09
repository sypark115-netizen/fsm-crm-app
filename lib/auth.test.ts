import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createSessionToken, verifySessionToken, verifyPassword } from './auth'

const ORIGINAL_ENV = { ...process.env }

describe('세션 토큰', () => {
  beforeEach(() => {
    process.env.SESSION_SECRET = 'test-secret'
  })
  afterEach(() => {
    process.env = { ...ORIGINAL_ENV }
    vi.useRealTimers()
  })

  it('생성한 토큰은 유효하다고 검증된다', () => {
    const token = createSessionToken()
    expect(verifySessionToken(token)).toBe(true)
  })

  it('변조된 토큰은 무효로 판정된다', () => {
    const token = createSessionToken()
    const tampered = token.slice(0, -1) + (token.endsWith('a') ? 'b' : 'a')
    expect(verifySessionToken(tampered)).toBe(false)
  })

  it('만료된 토큰은 무효로 판정된다', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    const token = createSessionToken()
    vi.setSystemTime(new Date('2026-01-09T00:00:00Z'))
    expect(verifySessionToken(token)).toBe(false)
  })

  it('빈 토큰은 무효로 판정된다', () => {
    expect(verifySessionToken(undefined)).toBe(false)
  })

  it('형식이 잘못된 토큰은 무효로 판정된다', () => {
    expect(verifySessionToken('not-a-valid-token')).toBe(false)
  })
})

describe('verifyPassword', () => {
  beforeEach(() => {
    process.env.ADMIN_PASSWORD = 'correct-password'
  })
  afterEach(() => {
    process.env = { ...ORIGINAL_ENV }
  })

  it('올바른 비밀번호면 true', () => {
    expect(verifyPassword('correct-password')).toBe(true)
  })

  it('틀린 비밀번호면 false', () => {
    expect(verifyPassword('wrong-password')).toBe(false)
  })
})
