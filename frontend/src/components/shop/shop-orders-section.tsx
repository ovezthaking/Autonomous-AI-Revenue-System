import type { Order } from "@/lib/api";

type ShopOrdersSectionProps = {
  orders: Order[];
};

export function ShopOrdersSection({ orders }: ShopOrdersSectionProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">Zamówienia</h2>
      {orders.length === 0 ? (
        <p className="text-sm text-gray-500">Brak zamówień.</p>
      ) : (
        <ul className="space-y-2">
          {orders.map((order) => (
            <li
              key={order.id}
              className="flex items-center justify-between rounded border p-3 text-sm"
            >
              <span>
                {order.provider} · {order.email ?? "brak e-maila"} ·{" "}
                {(order.amount_cents / 100).toFixed(2)} {order.currency}
              </span>
              <span className="font-mono text-xs">{order.status}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
