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

import { Client } from '@notionhq/client'
import { randomUUID } from 'crypto'
import { requireEnv } from './env'
import type { NewOrderInput } from '@/types/order'

let notionClient: Client | null = null
function getClient(): Client {
  if (!notionClient) notionClient = new Client({ auth: requireEnv('NOTION_TOKEN') })
  return notionClient
}

export function __clearNotionClient() {
  notionClient = null
}

function databaseId(): string {
  return requireEnv('NOTION_DATABASE_ID')
}

export async function listOrders(): Promise<Order[]> {
  const response = await getClient().databases.query({ database_id: databaseId() })
  return (response.results as unknown as NotionPage[]).map(mapPageToOrder)
}

export async function getOrderByToken(token: string): Promise<Order | null> {
  const response = await getClient().databases.query({
    database_id: databaseId(),
    filter: { property: PROPS.trackingToken, rich_text: { equals: token } },
  })
  const page = response.results[0] as unknown as NotionPage | undefined
  return page ? mapPageToOrder(page) : null
}

export async function createOrder(input: NewOrderInput): Promise<Order> {
  const trackingToken = randomUUID()
  const title = `${input.customerName} - ${new Date().toLocaleDateString('ko-KR')}`
  const page = await getClient().pages.create({
    parent: { database_id: databaseId() },
    properties: {
      [PROPS.title]: { title: [{ text: { content: title } }] },
      [PROPS.status]: { status: { name: '신규문의' } },
      [PROPS.brand]: { select: { name: input.brand } },
      [PROPS.customerType]: { select: { name: input.customerType } },
      [PROPS.inflowChannel]: { select: { name: input.inflowChannel } },
      [PROPS.customerName]: { rich_text: [{ text: { content: input.customerName } }] },
      [PROPS.phone]: { phone_number: input.phone ?? null },
      [PROPS.address]: { rich_text: [{ text: { content: input.address ?? '' } }] },
      [PROPS.trackingToken]: { rich_text: [{ text: { content: trackingToken } }] },
    },
  })
  return mapPageToOrder(page as unknown as NotionPage)
}

export async function updateOrderStatus(id: string, newStatus: OrderStatus): Promise<Order> {
  const current = await getClient().pages.retrieve({ page_id: id })
  const currentOrder = mapPageToOrder(current as unknown as NotionPage)
  const logLine = `[${new Date().toLocaleString('ko-KR')}] 상태변경: ${currentOrder.status}→${newStatus}`
  const newLog = currentOrder.timelineLog ? `${currentOrder.timelineLog}\n${logLine}` : logLine

  const page = await getClient().pages.update({
    page_id: id,
    properties: {
      [PROPS.status]: { status: { name: newStatus } },
      [PROPS.timelineLog]: { rich_text: [{ text: { content: newLog } }] },
    },
  })
  return mapPageToOrder(page as unknown as NotionPage)
}

export async function updateOrderFields(
  id: string,
  fields: Partial<Pick<Order, 'memo' | 'visitDate' | 'technician'>>
): Promise<Order> {
  const properties: Record<string, unknown> = {}
  if (fields.memo !== undefined) {
    properties[PROPS.memo] = { rich_text: [{ text: { content: fields.memo } }] }
  }
  if (fields.visitDate !== undefined) {
    properties[PROPS.visitDate] = fields.visitDate ? { date: { start: fields.visitDate } } : { date: null }
  }
  if (fields.technician !== undefined) {
    properties[PROPS.technician] = { rich_text: [{ text: { content: fields.technician } }] }
  }
  const page = await getClient().pages.update({ page_id: id, properties })
  return mapPageToOrder(page as unknown as NotionPage)
}
