import { readLibrary } from "@/lib/store";

export const dynamic = "force-dynamic";

/** 대시보드용 전체 데이터 (요약·메모 본문 제외) */
export async function GET() {
  return Response.json(await readLibrary());
}
