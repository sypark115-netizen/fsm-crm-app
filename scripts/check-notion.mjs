import { Client } from '@notionhq/client'
import { config } from 'dotenv'

config({ path: '.env.local' })

const token = process.env.NOTION_TOKEN
const databaseId = process.env.NOTION_DATABASE_ID

if (!token || !databaseId) {
  console.error('NOTION_TOKEN 또는 NOTION_DATABASE_ID가 .env.local에 설정되지 않았습니다.')
  process.exit(1)
}

const notion = new Client({ auth: token })

try {
  const database = await notion.databases.retrieve({ database_id: databaseId })
  console.log('연결 성공. 데이터베이스 제목:', database.title[0]?.plain_text ?? '(제목 없음)')
  console.log('속성 목록:', Object.keys(database.properties).join(', '))
} catch (error) {
  console.error('노션 연결 실패:', error.message)
  process.exit(1)
}
