'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    const response = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
    if (!response.ok) {
      const data = await response.json()
      setError(data.error ?? '로그인에 실패했습니다.')
      return
    }
    router.push('/board')
    router.refresh()
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-lg bg-white p-8 shadow">
        <h1 className="text-xl font-semibold">관리자 로그인</h1>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="공유 비밀번호"
          className="w-full rounded border px-3 py-2"
          autoFocus
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700">
          로그인
        </button>
      </form>
    </div>
  )
}
