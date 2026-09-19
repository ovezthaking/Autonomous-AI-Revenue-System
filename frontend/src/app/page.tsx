"use client";

import { useEffect, useState, useCallback } from "react";
import {
  decide,
  fetchContent,
  fetchRecentTasks,
  fetchRecommendations,
  runResearch,
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
  const [content, setContent] = useState<ContentItem[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [running, setRunning] = useState<boolean>(false);

  const reload = useCallback(async () => {
    const [r, c, t] = await Promise.all([
      fetchRecommendations("proposed"),
      fetchContent(),
      fetchRecentTasks(),
    ]);
    setProposed(r);
    setContent(c);
    setTasks(t);
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
        <h2 className="mb-3 text-lg font-medium">Content</h2>
        {content.length === 0 ? <p>No content drafts yet.</p> : null}
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
            </li>
          ))}
        </ul>
      </section>

      <section>
        <Button type="button" disabled={running} onClick={onRunResearch}>
          {running ? "Running research..." : "Run research"}
        </Button>
      </section>
    </main>
  );
}
