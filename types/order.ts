export type Brand = '아삽24' | '에어컨레벨업'
export type CustomerType = 'B2B/B2G' | 'B2C'
export type OrderStatus = '신규문의' | '방문/견적' | '작업완료' | '결제완료' | '리뷰완료'
export type InflowChannel = '당근마켓' | '네이버블로그' | '홈페이지' | '지인소개' | '기타'
export type TrackingStatus = '기사 배정 중' | '이동 중 / 작업 중' | '완료'

export const ORDER_STATUSES: OrderStatus[] = ['신규문의', '방문/견적', '작업완료', '결제완료', '리뷰완료']
export const BRANDS: Brand[] = ['아삽24', '에어컨레벨업']
export const CUSTOMER_TYPES: CustomerType[] = ['B2B/B2G', 'B2C']
export const INFLOW_CHANNELS: InflowChannel[] = ['당근마켓', '네이버블로그', '홈페이지', '지인소개', '기타']

export interface Order {
  id: string
  title: string
  status: OrderStatus
  brand: Brand
  customerType: CustomerType
  inflowChannel: InflowChannel
  customerName: string
  phone: string
  address: string
  visitDate: string | null
  quoteAmount: number | null
  paymentAmount: number | null
  technician: string
  memo: string
  timelineLog: string
  trackingToken: string
  photoLink: string | null
  createdAt: string
  updatedAt: string
}

export type NewOrderInput = {
  customerName: string
  phone?: string
  address?: string
  brand: Brand
  customerType: CustomerType
  inflowChannel: InflowChannel
}
