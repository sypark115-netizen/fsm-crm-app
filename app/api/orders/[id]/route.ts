import { NextRequest, NextResponse } from 'next/server'
import { updateOrderStatus, updateOrderFields } from '@/lib/notion'
import type { OrderStatus } from '@/types/order'

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const body = await request.json()
  try {
    if (body.status) {
      const order = await updateOrderStatus(id, body.status as OrderStatus)
      return NextResponse.json({ order })
    }
    const order = await updateOrderFields(id, body)
    return NextResponse.json({ order })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: '오더 수정에 실패했습니다.' }, { status: 502 })
  }
}
