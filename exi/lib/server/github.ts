// Minimal GitHub REST client for filing issues from feedback.
// Needs a fine-grained token with "Issues: read & write" on GITHUB_REPO (owner/name).

export function githubEnabled(): boolean {
  return Boolean(process.env.GITHUB_TOKEN && process.env.GITHUB_REPO);
}

async function post(path: string, body: unknown) {
  const base = process.env.GITHUB_API_URL || "https://api.github.com"; // GitHub Enterprise: https://HOST/api/v3
  return fetch(`${base}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      "User-Agent": "exi-feedback-agent",
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15_000),
  });
}

export async function createIssue(input: {
  title: string;
  body: string;
  labels?: string[];
}): Promise<{ number: number; url: string }> {
  const repo = process.env.GITHUB_REPO!;
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) throw new Error("GITHUB_REPO must look like owner/name");

  let res = await post(`/repos/${repo}/issues`, input);
  // Tokens without label permissions get 403/422 on labels — retry without them.
  if ((res.status === 403 || res.status === 422) && input.labels?.length) {
    res = await post(`/repos/${repo}/issues`, { title: input.title, body: input.body });
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`GitHub API ${res.status}: ${detail.slice(0, 200)}`);
  }
  const data = (await res.json()) as { number: number; html_url: string };
  return { number: data.number, url: data.html_url };
}
