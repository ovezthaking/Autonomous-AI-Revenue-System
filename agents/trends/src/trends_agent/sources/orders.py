"""Fulfilled orders signal source."""

from revenue_swarm.enums import OrderStatus
from revenue_swarm.models.order import Order
from revenue_swarm.models.product import Product
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class OrdersSource:
    name = "orders"

    def collect(self, db: Session) -> list[TrendSignal]:
        rows = db.execute(
            select(Order.product_id, func.count(Order.id))
            .where(Order.status == OrderStatus.FULFILLED.value)
            .group_by(Order.product_id)
        ).all()
        signals: list[TrendSignal] = []
        for product_id, count in rows:
            product = db.get(Product, product_id)
            if product is None or count <= 0:
                continue
            signals.append(
                TrendSignal(
                    source=self.name,
                    term=product.title,
                    value=float(count),
                    window_days=90,
                    raw={"product_id": str(product.id)},
                )
            )
        return signals
