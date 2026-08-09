'use client'

import { useState, type FormEvent } from 'react'
import { mutate } from 'swr'
import type { Brand, CustomerType, InflowChannel } from '@/types/order'
import { BRANDS, CUSTOMER_TYPES, INFLOW_CHANNELS } from '@/types/order'

export default function NewOrderModal({ onClose }: { onClose: () => void }) {
  const [customerName, setCustomerName] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [brand, setBrand] = useState<Brand>(BRANDS[0])
  const [customerType, setCustomerType] = useState<CustomerType>(CUSTOMER_TYPES[0])
  const [inflowChannel, setInflowChannel] = useState<InflowChannel>(INFLOW_CHANNELS[0])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customerName, phone, address, brand, customerType, inflowChannel }),
    })
    setSubmitting(false)
    if (!response.ok) {
      const data = await response.json()
      setError(data.error ?? '오더 생성에 실패했습니다.')
      return
    }
    mutate('/api/orders')
    onClose()
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/40">
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-3 rounded-lg bg-white p-6">
        <h2 className="text-lg font-semibold">신규문의 등록</h2>
        <input value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder="고객명" required className="w-full rounded border px-3 py-2" />
        <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="연락처" className="w-full rounded border px-3 py-2" />
        <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="주소" className="w-full rounded border px-3 py-2" />
        <select value={brand} onChange={(e) => setBrand(e.target.value as Brand)} className="w-full rounded border px-3 py-2">
          {BRANDS.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
        <select value={customerType} onChange={(e) => setCustomerType(e.target.value as CustomerType)} className="w-full rounded border px-3 py-2">
          {CUSTOMER_TYPES.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
        <select value={inflowChannel} onChange={(e) => setInflowChannel(e.target.value as InflowChannel)} className="w-full rounded border px-3 py-2">
          {INFLOW_CHANNELS.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-4 py-2">취소</button>
          <button type="submit" disabled={submitting} className="rounded bg-blue-600 px-4 py-2 text-white">
            {submitting ? '등록 중...' : '등록'}
          </button>
        </div>
      </form>
    </div>
  )
}
