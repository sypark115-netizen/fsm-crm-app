import type { Order, OrderStatus, TrackingStatus, Brand, CustomerType, InflowChannel } from '@/types/order'

export const PROPS = {
  title: '오더명',
  status: '상태',
  brand: '브랜드',
  customerType: '고객유형',
  inflowChannel: '유입경로',
  customerName: '고객명',
  phone: '연락처',
  address: '주소',
  visitDate: '방문예정일',
  quoteAmount: '견적금액',
  paymentAmount: '결제금액',
  technician: '담당기사',
  memo: '메모',
  timelineLog: '타임라인로그',
  trackingToken: '추적토큰',
  photoLink: '사진링크',
} as const

export interface NotionPropertyValue {
  title?: { plain_text: string }[]
  rich_text?: { plain_text: string }[]
  select?: { name: string } | null
  status?: { name: string } | null
  phone_number?: string | null
  number?: number | null
  date?: { start: string } | null
  url?: string | null
}

export interface NotionPage {
  id: string
  created_time: string
  last_edited_time: string
  properties: Record<string, NotionPropertyValue>
}

export function mapPageToOrder(page: NotionPage): Order {
  const p = page.properties
  return {
    id: page.id,
    title: p[PROPS.title]?.title?.[0]?.plain_text ?? '',
    status: (p[PROPS.status]?.status?.name ?? '신규문의') as OrderStatus,
    brand: (p[PROPS.brand]?.select?.name ?? '아삽24') as Brand,
    customerType: (p[PROPS.customerType]?.select?.name ?? 'B2C') as CustomerType,
    inflowChannel: (p[PROPS.inflowChannel]?.select?.name ?? '기타') as InflowChannel,
    customerName: p[PROPS.customerName]?.rich_text?.[0]?.plain_text ?? '',
    phone: p[PROPS.phone]?.phone_number ?? '',
    address: p[PROPS.address]?.rich_text?.[0]?.plain_text ?? '',
    visitDate: p[PROPS.visitDate]?.date?.start ?? null,
    quoteAmount: p[PROPS.quoteAmount]?.number ?? null,
    paymentAmount: p[PROPS.paymentAmount]?.number ?? null,
    technician: p[PROPS.technician]?.rich_text?.[0]?.plain_text ?? '',
    memo: p[PROPS.memo]?.rich_text?.[0]?.plain_text ?? '',
    timelineLog: p[PROPS.timelineLog]?.rich_text?.[0]?.plain_text ?? '',
    trackingToken: p[PROPS.trackingToken]?.rich_text?.[0]?.plain_text ?? '',
    photoLink: p[PROPS.photoLink]?.url ?? null,
    createdAt: page.created_time,
    updatedAt: page.last_edited_time,
  }
}

export function mapOrderStatusToTrackingStatus(status: OrderStatus): TrackingStatus {
  switch (status) {
    case '신규문의':
      return '기사 배정 중'
    case '방문/견적':
      return '이동 중 / 작업 중'
    case '작업완료':
    case '결제완료':
    case '리뷰완료':
      return '완료'
  }
}
