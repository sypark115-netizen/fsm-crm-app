import { NextRequest, NextResponse } from 'next/server'
import { verifySessionToken } from '@/lib/auth'

export const runtime = 'nodejs'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('session')?.value
  if (verifySessionToken(token)) {
    return NextResponse.next()
  }

  if (request.nextUrl.pathname.startsWith('/api/')) {
    return NextResponse.json({ error: '로그인이 필요합니다.' }, { status: 401 })
  }

  return NextResponse.redirect(new URL('/login', request.url))
}

export const config = {
  matcher: ['/board/:path*', '/dashboard/:path*', '/api/orders/:path*'],
}
