import { NextRequest, NextResponse } from 'next/server'
import { createSessionToken, verifyPassword } from '@/lib/auth'

export async function POST(request: NextRequest) {
  const { password } = await request.json()
  if (typeof password !== 'string' || !verifyPassword(password)) {
    return NextResponse.json({ error: '비밀번호가 올바르지 않습니다.' }, { status: 401 })
  }
  const token = createSessionToken()
  const response = NextResponse.json({ ok: true })
  response.cookies.set('session', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7,
    path: '/',
  })
  return response
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true })
  response.cookies.delete('session')
  return response
}
