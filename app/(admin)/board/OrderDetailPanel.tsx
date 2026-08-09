'use client'

import { useState } from 'react'
import useSWR, { mutate } from 'swr'
import { fetcher } from '@/lib/fetcher'
import type { Order } from '@/types/order'

export default function OrderDetailPanel({ orderId, onClose }: { orderId: string; onClose: () => void }) {
  const { data } = useSWR<{ orders: Order[] }>('/api/orders', fetcher)
  const order = data?.orders.find((item) => item.id === orderId)
  const [memo, setMemo] = useState(order?.memo ?? '')
  const [visitDate, setVisitDate] = useState(order?.visitDate ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!order) return null

  async function handleSave() {
    setSaving(true)
    setError(null)
    const response = await fetch(`/api/orders/${orderId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ memo, visitDate }),
    })
    setSaving(false)
    if (!response.ok) {
      const data = await response.json()
      setError(data.error ?? '저장에 실패했습니다.')
      return
    }
    mutate('/api/orders')
  }

  const timelineEntries = order.timelineLog.split('\n').filter(Boolean)

  return (
    <div className="fixed inset-0 flex justify-end bg-black/40">
      <div className="h-full w-full max-w-md space-y-4 overflow-y-auto bg-white p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{order.customerName}</h2>
          <button onClick={onClose}>닫기</button>
        </div>
        <p className="text-sm text-gray-500">{order.brand} · {order.customerType} · {order.status}</p>
        <div>
          <label className="text-sm font-medium">방문예정일</label>
          <input type="date" value={visitDate ?? ''} onChange={(e) => setVisitDate(e.target.value)} className="mt-1 w-full rounded border px-3 py-2" />
        </div>
        <div>
          <label className="text-sm font-medium">메모</label>
          <textarea value={memo} onChange={(e) => setMemo(e.target.value)} className="mt-1 w-full rounded border px-3 py-2" rows={3} />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button onClick={handleSave} disabled={saving} className="rounded bg-blue-600 px-4 py-2 text-white">
          {saving ? '저장 중...' : '저장'}
        </button>
        <div>
          <h3 className="mb-2 font-medium">타임라인</h3>
          <ul className="space-y-1 text-sm text-gray-600">
            {timelineEntries.length === 0 && <li>기록 없음</li>}
            {timelineEntries.map((entry, index) => <li key={index}>{entry}</li>)}
          </ul>
        </div>
      </div>
    </div>
  )
}
