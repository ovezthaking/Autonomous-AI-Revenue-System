"use client";

import { useEffect, useState, useCallback } from "react";
import {
  decide,
  decideContent,
  fetchContent,
  fetchRecentTasks,
  fetchRecommendations,
  publishDue,
  runContent,
  runResearch,
  scheduleContent,
  setAffiliateLink,
  type AgentTask,
  type ContentItem,
  type Recommendation,
} from "@/lib/api";
import { Button } from "@/components/ui/button";

function taskLabel(tasks: AgentTask[]): string {
  if (tasks.length === 0) return "idle";
  return tasks[0].status;
}

export default function DashboardPage() {
  const [proposed, setProposed] = useState<Recommendation[]>([]);
  const [approved, setApproved] = useState<Recommendation[]>([]);
  const [content, setContent] = useState<ContentItem[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [runningContent, setRunningContent] = useState<boolean>(false);
  const [publishing, setPublishing] = useState<boolean>(false);
  const [linkDrafts, setLinkDrafts] = useState<Record<string, string>>({});

  const reload = useCallback(async () => {
    const [proposedRows, approvedRows, contentRows, taskRows] =
      await Promise.all([
        fetchRecommendations("proposed"),
        fetchRecommendations("approved"),
        fetchContent(),
        fetchRecentTasks(),
      ]);
    setProposed(proposedRows);
    setApproved(approvedRows);
    setContent(contentRows);
    setTasks(taskRows);
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        await reload();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Błąd ładowania danych");
      }
    };

    init();

    const intervalId = setInterval(() => {
      reload().catch((e: Error) => console.error("Auto-refresh failed: ", e));
    }, 5000);

    return () => clearInterval(intervalId);
  }, [reload]);

  const onDecide = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    setError(null);
    try {
      await decide(id, action);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "decide failed");
    } finally {
      setBusyId(null);
    }
  };

  const onSaveLink = async (item: Recommendation) => {
    setBusyId(item.id);
    setError(null);
    try {
      const link = linkDrafts[item.id] ?? item.affiliate_link ?? "";
      await setAffiliateLink(item.id, link);
      setLinkDrafts((prev) => {
        const next = { ...prev };
        delete next[item.id];
        return next;
      });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "save link failed");
    } finally {
      setBusyId(null);
    }
  };

  const onRunResearch = async () => {
    setRunning(true);
    setError(null);
    try {
      await runResearch(5);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "research failed");
    } finally {
      setRunning(false);
    }
  };

  const onRunContent = async () => {
    setRunningContent(true);
    setError(null);
    try {
      await runContent(3);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "content failed");
    } finally {
      setRunningContent(false);
    }
  };

  const onDecideContent = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    setError(null);
    try {
      await decideContent(id, action);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "decide failed");
    } finally {
      setBusyId(null);
    }
  };

  const onSchedule = async (id: string) => {
    setBusyId(id);
    setError(null);
    try {
      await scheduleContent(id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "schedule failed");
    } finally {
      setBusyId(null);
    }
  };

  const onPublishDue = async () => {
    setPublishing(true);
    setError(null);
    try {
      await publishDue();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "publish failed");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl space-y-10 p-8">
      <h1 className="text-2xl font-semibold">HITL dashboard</h1>
      <p>
        Agent / last task: <strong>{taskLabel(tasks)}</strong>
      </p>
      {error ? <p className="text-red-600">{error}</p> : null}

      <section>
        <h2 className="mb-3 text-lg font-medium">Proposed programs</h2>
        {proposed.length === 0 ? <p>No pending recommendations.</p> : null}
        <ul className="space-y-4">
          {proposed.map((item) => (
            <li key={item.id} className="rounded border p-4">
              <div className="font-medium">{item.name}</div>
              {item.rationale ? (
                <p className="text-sm">{item.rationale}</p>
              ) : null}
              {item.url ? (
                <a className="text-sm underline" href={item.url}>
                  {item.url}
                </a>
              ) : null}
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={busyId === item.id}
                  onClick={() => onDecide(item.id, "approve")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={busyId === item.id}
                  onClick={() => onDecide(item.id, "reject")}
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Approved programs</h2>
        {approved.length === 0 ? <p>No approved programs.</p> : null}
        <ul className="space-y-4">
          {approved.map((item) => (
            <li key={item.id} className="rounded border p-4">
              <div className="font-medium">{item.name}</div>
              {item.rationale ? (
                <p className="text-sm">{item.rationale}</p>
              ) : null}
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  value={linkDrafts[item.id] ?? item.affiliate_link ?? ""}
                  onChange={(event) =>
                    setLinkDrafts((prev) => ({
                      ...prev,
                      [item.id]: event.target.value,
                    }))
                  }
                  placeholder="Affiliate link"
                  className="min-w-0 flex-1 rounded border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  disabled={busyId === item.id}
                  onClick={() => onSaveLink(item)}
                >
                  Save link
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Content</h2>
        {content.length === 0 ? <p>No content yet.</p> : null}
        <ul className="space-y-4">
          {content.map((item) => (
            <li key={item.id} className="rounded border p-4">
              <div className="font-medium">{item.title}</div>
              <pre className="mt-2 whitespace-pre-wrap text-sm">
                {item.body}
              </pre>
              <p className="text-xs">
                {item.channel} · {item.status}
              </p>
              {item.status === "draft" ? (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => onDecideContent(item.id, "approve")}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => onDecideContent(item.id, "reject")}
                  >
                    Reject
                  </button>
                </div>
              ) : null}
              {item.status === "approved" ? (
                <div className="mt-2">
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => onSchedule(item.id)}
                  >
                    Schedule
                  </button>
                </div>
              ) : null}
              {item.status === "published" ? (
                <p className="mt-2 text-xs">{item.published_at}</p>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-wrap gap-2">
        <Button type="button" disabled={running} onClick={onRunResearch}>
          {running ? "Running research..." : "Run research"}
        </Button>
        <Button type="button" disabled={runningContent} onClick={onRunContent}>
          {runningContent ? "Running content..." : "Run content"}
        </Button>
        <Button type="button" disabled={publishing} onClick={onPublishDue}>
          {publishing ? "Publishing..." : "Publish due"}
        </Button>
      </section>
    </main>
  );
}
