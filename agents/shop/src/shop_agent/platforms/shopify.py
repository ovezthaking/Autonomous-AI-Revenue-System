"""Shopify GraphQL implementation of ShopPlatform."""

from revenue_swarm import config
from revenue_swarm.enums import ListingStatus
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_listing import ProductListing

from shop_agent.listing import (
    clamp_price,
    format_price,
    handle_for,
    render_description,
)
from shop_agent.platforms.base import ListingResult
from shop_agent.shopify.graphql import execute, mutation_result

UPSERT_LISTING = """
mutation UpsertListing(
  $identifier: ProductSetIdentifiers!,
  $input: ProductSetInput!
) {
  productSet(identifier: $identifier, input: $input) {

    product {
      id
      handle
      status
      variants(first: 1) { nodes { id } }
    }
    userErrors { field message code }
  }
}
"""

COLLECTION_ADD = """
mutation CollectionAddProducts($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id }
    userErrors { field message }
  }
}
"""

PRODUCT_UPDATE = """
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id status }
    userErrors { field message }
  }
}
"""

PUBLISH = """
mutation PublishablePublish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable { ... on Product { id } }
    userErrors { field message }
  }
}
"""

FULFILLMENT_ORDERS = """
query OrderFulfillmentOrders($id: ID!) {
  order(id: $id) {
    fulfillmentOrders(first: 10) {
      nodes {
        id
        status
      }
    }
  }
}
"""

FULFILLMENT_CREATE = """
mutation FulfillmentCreate($fulfillment: FulfillmentV2Input!) {
  fulfillmentCreate(fulfillment: $fulfillment) {
    fulfillment { id status }
    userErrors { field message }
  }
}
"""


def _add_to_vat_collection(product_gid: str) -> None:
    if not config.SHOPIFY_VAT_COLLECTION_ID:
        return
    data = execute(
        COLLECTION_ADD,
        {
            "id": config.SHOPIFY_VAT_COLLECTION_ID,
            "productIds": [product_gid],
        },
    )
    mutation_result(data, "collectionAddProducts")


class ShopifyPlatform:
    name = "shopify"

    def upsert_listing(
        self, product: Product, status: ListingStatus
    ) -> ListingResult:
        shopify_status = (
            "ACTIVE" if status == ListingStatus.ACTIVE else "DRAFT"
        )
        variables = {
            "identifier": {"handle": handle_for(product)},
            "input": {
                "title": product.title,
                "handle": handle_for(product),
                "descriptionHtml": render_description(product),
                "status": shopify_status,
                "productType": "Digital download",
                "tags": ["digital", product.kind],
                "productOptions": [
                    {"name": "Format", "values": [{"name": "PDF"}]}
                ],
                "variants": [
                    {
                        "optionValues": [
                            {"optionName": "Format", "name": "PDF"}
                        ],
                        "price": format_price(
                            clamp_price(product.price_cents)
                        ),
                        "taxable": True,
                        "inventoryItem": {
                            "requiresShipping": False,
                            "tracked": False,
                        },
                    }
                ],
            },
        }
        data = execute(UPSERT_LISTING, variables)
        result = mutation_result(data, "productSet")
        node = result["product"]
        variants = (node.get("variants") or {}).get("nodes") or []
        variant_id = variants[0]["id"] if variants else None
        _add_to_vat_collection(node["id"])
        return ListingResult(node["id"], variant_id, node["handle"])

    def activate(self, listing: ProductListing) -> None:
        update_data = execute(
            PRODUCT_UPDATE,
            {"input": {"id": listing.external_id, "status": "ACTIVE"}},
        )
        if "productUpdate" in update_data:
            mutation_result(update_data, "productUpdate")
        data = execute(
            PUBLISH,
            {
                "id": listing.external_id,
                "input": {"publicationId": config.SHOPIFY_PUBLICATION_ID},
            },
        )
        mutation_result(data, "publishablePublish")

    def mark_fulfilled(self, order_gid: str) -> None:
        data = execute(FULFILLMENT_ORDERS, {"id": order_gid})
        nodes = ((data.get("order") or {}).get("fulfillmentOrders") or {}).get(
            "nodes"
        ) or []
        for node in nodes:
            node_status = str(node.get("status") or "OPEN").upper()
            if node_status not in {"OPEN", "IN_PROGRESS"}:
                continue
            result = execute(
                FULFILLMENT_CREATE,
                {
                    "fulfillment": {
                        "notifyCustomer": False,
                        "lineItemsByFulfillmentOrder": [
                            {"fulfillmentOrderId": node["id"]}
                        ],
                    }
                },
            )
            mutation_result(result, "fulfillmentCreate")
