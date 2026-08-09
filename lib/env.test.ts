import { describe, it, expect, afterEach } from 'vitest'
import { requireEnv, validateEnv } from './env'

const ORIGINAL_ENV = { ...process.env }

describe('requireEnv', () => {
  afterEach(() => {
    process.env = { ...ORIGINAL_ENV }
  })

  it('환경변수가 설정되어 있으면 값을 반환한다', () => {
    process.env.NOTION_TOKEN = 'secret_abc'
    expect(requireEnv('NOTION_TOKEN')).toBe('secret_abc')
  })

  it('환경변수가 없으면 에러를 던진다', () => {
    delete process.env.NOTION_TOKEN
    expect(() => requireEnv('NOTION_TOKEN')).toThrow('NOTION_TOKEN')
  })
})

describe('validateEnv', () => {
  afterEach(() => {
    process.env = { ...ORIGINAL_ENV }
  })

  it('모든 필수 환경변수가 있으면 에러 없이 통과한다', () => {
    process.env.NOTION_TOKEN = 'a'
    process.env.NOTION_DATABASE_ID = 'b'
    process.env.ADMIN_PASSWORD = 'c'
    process.env.SESSION_SECRET = 'd'
    expect(() => validateEnv()).not.toThrow()
  })

  it('하나라도 없으면 에러를 던진다', () => {
    process.env.NOTION_TOKEN = 'a'
    delete process.env.NOTION_DATABASE_ID
    process.env.ADMIN_PASSWORD = 'c'
    process.env.SESSION_SECRET = 'd'
    expect(() => validateEnv()).toThrow('NOTION_DATABASE_ID')
  })
})
