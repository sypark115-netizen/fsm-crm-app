import { NextRequest, NextResponse } from 'next/server'
import { listOrders, createOrder } from '@/lib/notion'
import type { NewOrderInput } from '@/types/order'

export async function GET() {
  try {
    const orders = await listOrders()
    return NextResponse.json({ orders })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: '노션 연결에 실패했습니다. 잠시 후 다시 시도해주세요.' }, { status: 502 })
  }
}

export async function POST(request: NextRequest) {
  const input = (await request.json()) as NewOrderInput
  if (!input.customerName || !input.brand || !input.customerType || !input.inflowChannel) {
    return NextResponse.json({ error: '필수 항목이 누락되었습니다.' }, { status: 400 })
  }
  try {
    const order = await createOrder(input)
    return NextResponse.json({ order }, { status: 201 })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: '오더 생성에 실패했습니다.' }, { status: 502 })
  }
}
