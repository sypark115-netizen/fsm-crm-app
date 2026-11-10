import { uid } from "../ids";
import type { AgentId, FeedbackItem, User } from "../types";
import { claudeEnabled, triageWithClaude, type Triage } from "./claude";
import { createIssue, githubEnabled } from "./github";
import { saveFeedback } from "./repo";

// Feedback → Claude triage → GitHub issue. Every step is appended to a log
// that streams to all clients, so the team sees the improvement loop live.

function heuristicTriage(text: string): Triage {
  const bug = /bug|broken|error|crash|slow|doesn'?t work|오류|버그|느려|안\s?돼/i.test(text);
  const firstLine = text.split("\n")[0].trim();
  return {
    title: (firstLine.length > 70 ? `${firstLine.slice(0, 67)}…` : firstLine) || "User feedback",
    kind: bug ? "bug" : "enhancement",
    priority: bug ? "P1" : "P2",
    area: "General",
    body: `### Feedback\n${text}\n\n### Acceptance criteria\n- [ ] Clarify with the reporter\n- [ ] Implement and verify`,
  };
}

export function submitFeedback(text: string, user: User): FeedbackItem {
  let item: FeedbackItem = {
    id: uid("fb"),
    text,
    createdAt: Date.now(),
    createdBy: user.id,
    status: "received",
    log: [],
  };
  const log = (agent: AgentId, line: string, patch: Partial<FeedbackItem> = {}) => {
    item = { ...item, ...patch, log: [...item.log, { at: Date.now(), agent, text: line }] };
    saveFeedback(item);
  };
  log("exi", `Received feedback from ${user.displayName}. Routing to Analyst for triage.`);

  void (async () => {
    try {
      log("analyst", "Triaging…", { status: "triaging" });
      const triage = claudeEnabled() ? await triageWithClaude(text) : heuristicTriage(text);
      log("analyst", `Classified as **${triage.kind}** in _${triage.area}_ · ${triage.priority}: “${triage.title}”`, {
        title: triage.title,
        kind: triage.kind,
        priority: triage.priority,
      });

      if (!githubEnabled()) {
        log("planner", "Saved to the in-app backlog. Set `GITHUB_TOKEN` and `GITHUB_REPO` to file GitHub issues.", {
          status: "filed",
        });
        return;
      }
      const issue = await createIssue({
        title: triage.title,
        body: `${triage.body}\n\n---\n**Type:** ${triage.kind} · **Priority:** ${triage.priority} · **Area:** ${triage.area}\n\n<details><summary>Original feedback (${user.displayName})</summary>\n\n${text}\n</details>\n\n_Filed by Exi's feedback agent._`,
        labels: [triage.kind, triage.priority, "from-exi"],
      });
      log("planner", `Filed GitHub issue [#${issue.number}](${issue.url}) for the dev team.`, {
        status: "filed",
        issueUrl: issue.url,
      });
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      console.error("[exi] feedback processing failed", err);
      log("exi", `⚠️ Couldn't file this: ${error}`, { status: "failed" });
    }
  })();

  return item;
}
