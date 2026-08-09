'use client'

import useSWR, { mutate } from 'swr'
import { DndContext, type DragEndEvent, useDraggable, useDroppable } from '@dnd-kit/core'
import { useState } from 'react'
import type { Order, OrderStatus, Brand } from '@/types/order'
import { ORDER_STATUSES } from '@/types/order'
import { fetcher } from '@/lib/fetcher'

export default function KanbanBoard() {
  const { data, error } = useSWR<{ orders: Order[] }>('/api/orders', fetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  })
  const [brandFilter, setBrandFilter] = useState<Brand | '전체'>('전체')
  const [dragError, setDragError] = useState<string | null>(null)

  const orders = (data?.orders ?? []).filter(
    (order) => brandFilter === '전체' || order.brand === brandFilter
  )

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over) return
    const orderId = String(active.id)
    const newStatus = over.id as OrderStatus
    const current = data?.orders ?? []
    const target = current.find((order) => order.id === orderId)
    if (!target || target.status === newStatus) return

    const optimistic = current.map((order) =>
      order.id === orderId ? { ...order, status: newStatus } : order
    )
    mutate('/api/orders', { orders: optimistic }, false)

    const response = await fetch(`/api/orders/${orderId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    })

    if (!response.ok) {
      setDragError('상태 변경에 실패했습니다. 잠시 후 다시 시도해주세요.')
      mutate('/api/orders', { orders: current }, false)
    } else {
      mutate('/api/orders')
    }
  }

  if (error) return <p className="p-8 text-red-600">{error.message}</p>
  if (!data) return <p className="p-8">불러오는 중...</p>

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-2">
          {(['전체', '아삽24', '에어컨레벨업'] as const).map((brand) => (
            <button
              key={brand}
              onClick={() => setBrandFilter(brand)}
              className={`rounded px-3 py-1 text-sm ${
                brandFilter === brand ? 'bg-blue-600 text-white' : 'bg-gray-200'
              }`}
            >
              {brand}
            </button>
          ))}
        </div>
      </div>

      {dragError && <p className="mb-4 text-sm text-red-600">{dragError}</p>}

      <DndContext onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-5 gap-4">
          {ORDER_STATUSES.map((status) => (
            <BoardColumn key={status} status={status} orders={orders.filter((order) => order.status === status)} />
          ))}
        </div>
      </DndContext>
    </div>
  )
}

function BoardColumn({ status, orders }: { status: OrderStatus; orders: Order[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  return (
    <div
      ref={setNodeRef}
      className={`min-h-[400px] rounded-lg border-2 p-2 ${
        isOver ? 'border-blue-400 bg-blue-50' : 'border-transparent bg-gray-100'
      }`}
    >
      <h2 className="mb-2 font-semibold">{status}</h2>
      {orders.map((order) => (
        <OrderCard key={order.id} order={order} />
      ))}
    </div>
  )
}

function OrderCard({ order }: { order: Order }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: order.id })
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes} className="mb-2 cursor-pointer rounded bg-white p-3 shadow">
      <div className="flex gap-1 text-xs">
        <span className="rounded bg-purple-100 px-1.5 py-0.5">{order.brand}</span>
        <span className="rounded bg-green-100 px-1.5 py-0.5">{order.customerType}</span>
      </div>
      <p className="mt-1 font-medium">{order.customerName}</p>
      {order.visitDate && <p className="text-xs text-gray-500">{order.visitDate}</p>}
      {order.quoteAmount !== null && <p className="text-xs text-gray-500">{order.quoteAmount.toLocaleString()}원</p>}
    </div>
  )
}
