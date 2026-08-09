import { notFound } from 'next/navigation'
import { getOrderByToken, mapOrderStatusToTrackingStatus } from '@/lib/notion'

export default async function TrackPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  const order = await getOrderByToken(token)
  if (!order) notFound()

  const trackingStatus = mapOrderStatusToTrackingStatus(order.status)

  return (
    <div className="mx-auto max-w-md p-8">
      <h1 className="text-xl font-semibold">{order.brand} 작업 현황</h1>
      <p className="mt-4 text-lg">
        현재 상태: <span className="font-bold">{trackingStatus}</span>
      </p>
      {order.visitDate && <p className="mt-2 text-gray-600">방문예정일: {order.visitDate}</p>}
    </div>
  )
}
