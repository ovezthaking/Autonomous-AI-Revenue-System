"use client";

import { useState } from "react";
import {
  ActionTriggersBar,
  ApplicationsSection,
  ApprovedProgramsSection,
  BrokenLinksSection,
  ContentItemsSection,
  ContentMetricsTable,
  DashboardHeader,
  DashboardTabs,
  NeedsReviewSection,
  OrdersSection,
  ProductsSection,
  ProposedProgramsSection,
  RejectedProgramsSection,
} from "@/components/dashboard";
import { useDashboard } from "@/hooks/use-dashboard";
import type { DashboardTab } from "@/lib/api";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<DashboardTab>("all");
  const {
    proposed,
    approved,
    rejected,
    applications,
    brokenLinks,
    contentMetrics,
    content,
    tasks,
    products,
    orders,
    needsReview,
    error,
    setError,
    busyId,
    runningResearch,
    runningContent,
    publishing,
    proposingProducts,
    onDecideProgram,
    onSaveLink,
    onMarkApplied,
    onMarkActive,
    onMarkDeclined,
    onRepairLink,
    onDecideContent,
    onScheduleContent,
    onResolvePublication,
    onDecideProduct,
    onRecordReview,
    onRetryChapters,
    onOpenAsset,
    onProposeProducts,
    onRunResearch,
    onRunContent,
    onPublishDue,
  } = useDashboard();

  const showProducts = activeTab === "all" || activeTab === "products";
  const showOrders = activeTab === "all" || activeTab === "orders";
  const showPrograms = activeTab === "all" || activeTab === "programs";
  const showContent = activeTab === "all" || activeTab === "content";

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-6 md:p-8">
      <DashboardHeader tasks={tasks} />

      {error ? (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          <strong>Error:</strong> {error}
        </div>
      ) : null}

      <DashboardTabs
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        counts={{
          products: products.length,
          orders: orders.length,
          programs: proposed.length,
          content: content.length,
        }}
      />

      {showContent ? (
        <NeedsReviewSection
          needsReview={needsReview}
          busyId={busyId}
          onResolvePublication={(id, resolution, externalId) =>
            void onResolvePublication(id, resolution, externalId)
          }
        />
      ) : null}

      {showProducts ? (
        <ProductsSection
          products={products}
          busyId={busyId}
          proposingProducts={proposingProducts}
          onProposeProducts={(niche) => void onProposeProducts(niche)}
          onDecideProduct={(product, action) =>
            void onDecideProduct(product, action)
          }
          onRecordReview={(productId, reviewer) =>
            void onRecordReview(productId, reviewer)
          }
          onRetryChapters={onRetryChapters}
          onOpenAsset={(productId, assetType) =>
            void onOpenAsset(productId, assetType)
          }
          onError={(msg) => setError(msg)}
        />
      ) : null}

      {showOrders ? (
        <OrdersSection orders={orders} products={products} />
      ) : null}

      {showPrograms ? (
        <>
          <ProposedProgramsSection
            proposed={proposed}
            busyId={busyId}
            onDecideProgram={(id, action) => void onDecideProgram(id, action)}
          />
          <ApprovedProgramsSection
            approved={approved}
            busyId={busyId}
            onSaveLink={onSaveLink}
          />
          <RejectedProgramsSection rejected={rejected} />
          <ApplicationsSection
            applications={applications}
            busyId={busyId}
            onMarkApplied={(id) => void onMarkApplied(id)}
            onMarkActive={(id, network, programId) =>
              void onMarkActive(id, network, programId)
            }
            onMarkDeclined={(id) => void onMarkDeclined(id)}
          />
          <BrokenLinksSection
            brokenLinks={brokenLinks}
            busyId={busyId}
            onRepairLink={onRepairLink}
          />
        </>
      ) : null}

      {showContent || showPrograms ? (
        <ContentMetricsTable contentMetrics={contentMetrics} />
      ) : null}

      {showContent ? (
        <ContentItemsSection
          content={content}
          busyId={busyId}
          onDecideContent={(id, action) => void onDecideContent(id, action)}
          onScheduleContent={(id) => void onScheduleContent(id)}
        />
      ) : null}

      <ActionTriggersBar
        runningResearch={runningResearch}
        runningContent={runningContent}
        publishing={publishing}
        onRunResearch={() => void onRunResearch()}
        onRunContent={() => void onRunContent()}
        onPublishDue={() => void onPublishDue()}
      />
    </main>
  );
}
