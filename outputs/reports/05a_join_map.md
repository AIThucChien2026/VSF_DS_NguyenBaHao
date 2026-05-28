# Join map

products.product_id -> order_items.product_id, returns.product_id, reviews.product_id, inventory.product_id
customers.customer_id -> orders.customer_id, reviews.customer_id
geography.zip -> customers.zip, orders.zip
orders.order_id -> order_items.order_id, payments.order_id, shipments.order_id, returns.order_id, reviews.order_id
promotions.promo_id -> order_items.promo_id, order_items.promo_id_2

## Notes

- Do not join every table at once.
- Joining orders to order_items changes granularity from order-level to item-level.
- Aggregate many-row tables before order-level analysis.
- Use sales.csv as the central table for forecasting exploration.
