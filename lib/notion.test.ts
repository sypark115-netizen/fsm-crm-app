import { describe, it, expect } from 'vitest'
import { mapPageToOrder, mapOrderStatusToTrackingStatus, type NotionPage } from './notion'

const FIXTURE_PAGE: NotionPage = {
  id: 'page-1',
  created_time: '2026-01-01T00:00:00.000Z',
  last_edited_time: '2026-01-02T00:00:00.000Z',
  properties: {
    오더명: { title: [{ plain_text: '홍길동 - 2026.01.01' }] },
    상태: { status: { name: '신규문의' } },
    브랜드: { select: { name: '아삽24' } },
    고객유형: { select: { name: 'B2C' } },
    유입경로: { select: { name: '당근마켓' } },
    고객명: { rich_text: [{ plain_text: '홍길동' }] },
    연락처: { phone_number: '010-1234-5678' },
    주소: { rich_text: [{ plain_text: '서울시 강남구' }] },
    방문예정일: { date: null },
    견적금액: { number: null },
    결제금액: { number: null },
    담당기사: { rich_text: [] },
    메모: { rich_text: [] },
    타임라인로그: { rich_text: [{ plain_text: '[2026-01-01] 상태변경: →신규문의' }] },
    추적토큰: { rich_text: [{ plain_text: 'token-abc-123' }] },
    사진링크: { url: null },
  },
}

describe('mapPageToOrder', () => {
  it('노션 페이지 속성을 Order로 변환한다', () => {
    const order = mapPageToOrder(FIXTURE_PAGE)
    expect(order).toEqual({
      id: 'page-1',
      title: '홍길동 - 2026.01.01',
      status: '신규문의',
      brand: '아삽24',
      customerType: 'B2C',
      inflowChannel: '당근마켓',
      customerName: '홍길동',
      phone: '010-1234-5678',
      address: '서울시 강남구',
      visitDate: null,
      quoteAmount: null,
      paymentAmount: null,
      technician: '',
      memo: '',
      timelineLog: '[2026-01-01] 상태변경: →신규문의',
      trackingToken: 'token-abc-123',
      photoLink: null,
      createdAt: '2026-01-01T00:00:00.000Z',
      updatedAt: '2026-01-02T00:00:00.000Z',
    })
  })

  it('빈 속성은 안전한 기본값으로 채운다', () => {
    const emptyPage: NotionPage = {
      id: 'page-2',
      created_time: '2026-01-01T00:00:00.000Z',
      last_edited_time: '2026-01-01T00:00:00.000Z',
      properties: {},
    }
    const order = mapPageToOrder(emptyPage)
    expect(order.customerName).toBe('')
    expect(order.status).toBe('신규문의')
    expect(order.visitDate).toBeNull()
  })
})

describe('mapOrderStatusToTrackingStatus', () => {
  it('신규문의는 기사 배정 중으로 매핑된다', () => {
    expect(mapOrderStatusToTrackingStatus('신규문의')).toBe('기사 배정 중')
  })

  it('방문/견적은 이동 중 / 작업 중으로 매핑된다', () => {
    expect(mapOrderStatusToTrackingStatus('방문/견적')).toBe('이동 중 / 작업 중')
  })

  it('작업완료/결제완료/리뷰완료는 완료로 매핑된다', () => {
    expect(mapOrderStatusToTrackingStatus('작업완료')).toBe('완료')
    expect(mapOrderStatusToTrackingStatus('결제완료')).toBe('완료')
    expect(mapOrderStatusToTrackingStatus('리뷰완료')).toBe('완료')
  })
})
