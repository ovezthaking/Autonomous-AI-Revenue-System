import type { DashboardTab } from "@/lib/api";

type DashboardTabsProps = {
  activeTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  counts: {
    products: number;
    orders: number;
    programs: number;
    content: number;
  };
};

export function DashboardTabs({
  activeTab,
  onSelectTab,
  counts,
}: DashboardTabsProps) {
  const tabs: Array<{ id: DashboardTab; label: string; count?: number }> = [
    { id: "all", label: "All Views" },
    { id: "products", label: "E-books & Products", count: counts.products },
    { id: "orders", label: "Orders", count: counts.orders },
    { id: "programs", label: "Programs", count: counts.programs },
    { id: "content", label: "Content", count: counts.content },
  ];

  return (
    <div className="flex flex-wrap gap-2 border-b pb-3 text-sm">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSelectTab(tab.id)}
            className={`flex items-center gap-1.5 rounded px-3 py-1.5 transition-colors ${
              isActive
                ? "bg-neutral-900 font-medium text-white"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined ? (
              <span className="rounded-full bg-neutral-200 px-1.5 py-0.2 text-xs text-neutral-800">
                {tab.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
