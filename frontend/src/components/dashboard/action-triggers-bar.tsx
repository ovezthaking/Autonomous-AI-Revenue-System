import { Button } from "@/components/ui/button";

type ActionTriggersBarProps = {
  runningResearch: boolean;
  runningContent: boolean;
  publishing: boolean;
  onRunResearch: () => void;
  onRunContent: () => void;
  onPublishDue: () => void;
};

export function ActionTriggersBar({
  runningResearch,
  runningContent,
  publishing,
  onRunResearch,
  onRunContent,
  onPublishDue,
}: ActionTriggersBarProps) {
  return (
    <section className="flex flex-wrap gap-2 border-t pt-4">
      <Button type="button" disabled={runningResearch} onClick={onRunResearch}>
        {runningResearch ? "Running research..." : "Run research (5)"}
      </Button>
      <Button type="button" disabled={runningContent} onClick={onRunContent}>
        {runningContent ? "Running content..." : "Run content (3)"}
      </Button>
      <Button type="button" disabled={publishing} onClick={onPublishDue}>
        {publishing ? "Publishing..." : "Publish due"}
      </Button>
    </section>
  );
}
