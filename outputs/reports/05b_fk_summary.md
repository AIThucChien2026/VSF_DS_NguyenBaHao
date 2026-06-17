# Báo cáo FK Integrity (05b)

Kiểm tra toàn vẹn tham chiếu (referential integrity) cho tất cả quan hệ FK → PK.
Nullable FK (`promo_id`, `promo_id_2`) chỉ check các row không null — null là hợp lệ nghiệp vụ.

---

## Tổng quan

| Chỉ số | Giá trị |
|---|---|
| Tổng số FK relationships kiểm tra | 13 |
| Relationships PASS | 13 |
| Relationships FAIL | 0 |
| Tổng orphan rows phát hiện | 0 |

---

## FK vi phạm (FAIL) — Orphan records

*Tất cả FK relationships đều hợp lệ — không có orphan record.*

---

## FK hợp lệ (PASS)

| child_table   | fk_column   | parent_table   | pk_column   |   checked_rows |
|:--------------|:------------|:---------------|:------------|---------------:|
| orders        | customer_id | customers      | customer_id |         646945 |
| orders        | zip         | geography      | zip         |         646945 |
| order_items   | order_id    | orders         | order_id    |         714669 |
| order_items   | product_id  | products       | product_id  |         714669 |
| order_items   | promo_id    | promotions     | promo_id    |         276316 |
| order_items   | promo_id_2  | promotions     | promo_id    |            206 |
| payments      | order_id    | orders         | order_id    |         646945 |
| shipments     | order_id    | orders         | order_id    |         566067 |
| returns       | order_id    | orders         | order_id    |          39939 |
| returns       | product_id  | products       | product_id  |          39939 |
| reviews       | order_id    | orders         | order_id    |         113551 |
| reviews       | product_id  | products       | product_id  |         113551 |
| inventory     | product_id  | products       | product_id  |          60247 |

---

## Khuyến nghị xử lý

- Chi tiết orphan rows lưu trong `05b_fk_violations.csv` kèm `_child_table`, `_fk_column` để truy vết.
- Nếu `percent_valid < 100%`: kiểm tra ETL/nguồn dữ liệu trước khi join —
  orphan rows sẽ bị drop khi INNER JOIN.
- Nếu cần giữ orphan rows: dùng LEFT JOIN và xử lý null sau join.
- Nullable FK (`promo_id`, `promo_id_2`): null không tính là orphan, đây là hành vi đúng nghiệp vụ.
