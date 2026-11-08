import type { Order, Product } from "@/lib/api";
import { formatPrice, orderStatusBadge } from "@/lib/formatters";

type OrdersSectionProps = {
  orders: Order[];
  products: Product[];
};

export function OrdersSection({ orders, products }: OrdersSectionProps) {
  return (
    <section className="space-y-4 rounded-lg border bg-neutral-50/60 p-5">
      <div>
        <h2 className="text-lg font-semibold text-neutral-900">
          Customer Orders &amp; Fulfillment
        </h2>
        <p className="text-xs text-neutral-500">
          Checkout sessions, webhook fulfillment status, and download grants
        </p>
      </div>
      {orders.length === 0 ? (
        <p className="text-sm text-neutral-500">No orders recorded yet.</p>
      ) : (
        <div className="space-y-2">
          {orders.map((order) => {
            const matchedProduct = products.find(
              (p) => p.id === order.product_id,
            );
            return (
              <div
                key={order.id}
                className="flex flex-col justify-between gap-2 rounded border bg-white p-3 text-xs sm:flex-row sm:items-center"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-neutral-900">
                      {matchedProduct?.title ?? order.product_id}
                    </span>
                    <span className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-[11px] uppercase text-neutral-700">
                      {order.provider}
                    </span>
                    <span
                      className={`rounded px-2 py-0.5 font-medium uppercase ${orderStatusBadge(
                        order.status,
                      )}`}
                    >
                      {order.status}
                    </span>
                  </div>
                  <div className="text-neutral-500">
                    Session:{" "}
                    <code className="font-mono">
                      {order.provider_session_id}
                    </code>
                    {order.email ? ` • Buyer: ${order.email}` : ""}
                  </div>
                </div>
                <div className="text-right font-mono font-semibold text-neutral-900">
                  {formatPrice(order.amount_cents, order.currency)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
