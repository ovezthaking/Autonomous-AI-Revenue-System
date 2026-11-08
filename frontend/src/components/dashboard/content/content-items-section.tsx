import { Button } from "@/components/ui/button";
import type { ContentItem } from "@/lib/api";

type ContentItemsSectionProps = {
  content: ContentItem[];
  busyId: string | null;
  onDecideContent: (id: string, action: "approve" | "reject") => void;
  onScheduleContent: (id: string) => void;
};

export function ContentItemsSection({
  content,
  busyId,
  onDecideContent,
  onScheduleContent,
}: ContentItemsSectionProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">Content items</h2>
      {content.length === 0 ? (
        <p className="text-sm text-neutral-500">No content generated yet.</p>
      ) : null}
      <ul className="space-y-4">
        {content.map((item) => (
          <li key={item.id} className="space-y-2 rounded border bg-white p-4">
            <div className="font-medium">{item.title}</div>
            <pre className="whitespace-pre-wrap rounded bg-neutral-50 p-2 font-sans text-xs text-neutral-800">
              {item.body}
            </pre>
            <div className="flex items-center gap-2 text-xs text-neutral-500">
              <span>{item.channel}</span> &bull; <span>{item.status}</span>{" "}
              &bull; <span>Contains disclosure</span>
            </div>
            {item.status === "draft" ? (
              <div className="mt-2 flex gap-2">
                <Button
                  size="sm"
                  disabled={busyId === item.id}
                  onClick={() => onDecideContent(item.id, "approve")}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={busyId === item.id}
                  onClick={() => onDecideContent(item.id, "reject")}
                >
                  Reject
                </Button>
              </div>
            ) : null}
            {item.status === "approved" ? (
              <div className="mt-2">
                <Button
                  size="sm"
                  disabled={busyId === item.id}
                  onClick={() => onScheduleContent(item.id)}
                >
                  Schedule
                </Button>
              </div>
            ) : null}
            {item.status === "published" ? (
              <p className="mt-2 text-xs text-neutral-500">
                Published at: {item.published_at}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
