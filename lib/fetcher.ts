export async function fetcher(url: string) {
  const response = await fetch(url)
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error ?? '요청에 실패했습니다.')
  }
  return data
}
