# Relationship Analysis (07)

## Overview

Step 5 explores relationships that may inform forecasting features. Each analysis uses only the tables needed for that relationship and keeps a clear grain.

## Validation Checks

| check                              | value               |
|:-----------------------------------|:--------------------|
| sales_rows                         | 3833                |
| web_daily_rows                     | 3652                |
| merged_rows                        | 3833                |
| missing_web_rows_after_left_join   | 181                 |
| sales_date_min                     | 2012-07-04 00:00:00 |
| sales_date_max                     | 2022-12-31 00:00:00 |
| web_date_min                       | 2013-01-01 00:00:00 |
| web_date_max                       | 2022-12-31 00:00:00 |
| order_items_rows                   | 714669              |
| item_base_rows                     | 714669              |
| missing_product_rows               | 0                   |
| negative_net_item_revenue_rows     | 0                   |
| non_positive_gross_item_value_rows | 0                   |
| orders_rows                        | 646945              |
| shipments_rows                     | 566067              |
| review_orders                      | 111369              |
| leadtime_base_rows                 | 111369              |
| negative_ship_lead_rows            | 0                   |
| negative_delivery_lead_rows        | 0                   |
| ratings_outside_1_5_rows           | 0                   |

## Revenue vs Traffic: Strongest Correlations

| sales_metric   | traffic_metric       |   pearson_corr |   non_null_pairs |
|:---------------|:---------------------|---------------:|-----------------:|
| COGS           | sessions_rolling_7d  |       0.329196 |             3652 |
| COGS           | sessions_lag_1d      |       0.325442 |             3651 |
| Revenue        | sessions_rolling_7d  |       0.325342 |             3652 |
| COGS           | sessions             |       0.323547 |             3652 |
| Revenue        | sessions_lag_1d      |       0.321606 |             3651 |
| Revenue        | sessions             |       0.32105  |             3652 |
| COGS           | unique_visitors      |       0.32015  |             3652 |
| Revenue        | unique_visitors      |       0.318787 |             3652 |
| COGS           | sessions_lag_7d      |       0.312702 |             3645 |
| Revenue        | sessions_lag_7d      |       0.309202 |             3645 |
| COGS           | sessions_rolling_30d |       0.308363 |             3652 |
| COGS           | page_views           |       0.303177 |             3652 |

## Discount vs Estimated Profit

| discount_bin   |   item_rows |     revenue |   estimated_profit |   avg_margin |   profit_margin_weighted |
|:---------------|------------:|------------:|-------------------:|-------------:|-------------------------:|
| 0              |      438353 | 1.0995e+10  |        2.19502e+09 |    0.203133  |                0.201114  |
| 0-5%           |       20852 | 3.71375e+08 |       -2.35003e+08 |   -0.625653  |               -0.632791  |
| 5-10%          |       26378 | 5.66469e+08 |        4.94838e+06 |    0.0198554 |                0.0199182 |
| 10-20%         |      203186 | 3.44951e+09 |       -3.7424e+08  |   -0.117441  |               -0.110894  |
| 20%+           |       25900 | 2.98479e+08 |       -7.33023e+07 |   -0.243164  |               -0.243764  |

## Lead Time vs Rating Correlation

| relationship                     |   pearson_corr |   non_null_pairs |
|:---------------------------------|---------------:|-----------------:|
| ship_lead_days vs avg_rating     |   -0.000138366 |           111369 |
| delivery_lead_days vs avg_rating |   -0.00529499  |           111369 |
| review_delay_days vs avg_rating  |   -0.00143378  |           111369 |

## Category and Segment Margin Highlights

| group_field   | group_value   |   item_rows |   quantity |   products |     revenue |   estimated_profit |   avg_margin |   profit_margin_weighted |
|:--------------|:--------------|------------:|-----------:|-----------:|------------:|-------------------:|-------------:|-------------------------:|
| category      | Streetwear    |      393533 |    1768826 |        877 | 1.25585e+10 |        1.16581e+09 |    0.0588594 |                0.0928303 |
| category      | Outdoor       |      259986 |    1170000 |        496 | 2.3534e+09  |        2.67034e+08 |    0.0811266 |                0.113468  |
| category      | GenZ          |       37159 |     166848 |        111 | 3.2871e+08  |        5.08364e+07 |    0.149514  |                0.154654  |
| category      | Casual        |       23991 |     107469 |        114 | 4.40285e+08 |        3.37408e+07 |    0.0341602 |                0.0766339 |
| segment       | Everyday      |      182533 |     819449 |        319 | 5.14745e+09 |        5.32175e+08 |    0.0677001 |                0.103386  |
| segment       | Balanced      |      103333 |     464217 |        201 | 4.90032e+09 |        4.31236e+08 |    0.0574717 |                0.0880016 |
| segment       | Activewear    |      230375 |    1036857 |        430 | 1.9307e+09  |        2.4634e+08  |    0.0880082 |                0.12759   |
| segment       | Performance   |       96730 |     435685 |        244 | 2.28503e+09 |        1.73694e+08 |    0.0403088 |                0.0760138 |
| segment       | Trendy        |       37159 |     166848 |        111 | 3.2871e+08  |        5.08364e+07 |    0.149514  |                0.154654  |

## Feature Candidates

| feature_name                                   | source_tables               | grain                   | why_useful                                                              | leakage_risk                                                             | recommended_use                                                                     |
|:-----------------------------------------------|:----------------------------|:------------------------|:------------------------------------------------------------------------|:-------------------------------------------------------------------------|:------------------------------------------------------------------------------------|
| sessions_lag_1d / sessions_lag_7d              | web_traffic                 | daily                   | Captures recent demand/traffic signal before revenue is observed.       | LOW if only past traffic is used.                                        | Use lagged traffic features for daily revenue/COGS forecasting.                     |
| sessions_rolling_7d / sessions_rolling_30d     | web_traffic                 | daily                   | Smooths noisy traffic and captures short/medium-term demand trend.      | LOW if rolling window excludes future days.                              | Use rolling features computed up to prediction date.                                |
| discount_rate_bin_share                        | order_items, products       | item/monthly aggregate  | Discount intensity may explain revenue lift and margin pressure.        | MEDIUM; future discounts are only usable if promotion calendar is known. | Aggregate by month/category and use known planned discounts or lagged discount mix. |
| category_revenue_share / segment_revenue_share | order_items, products       | item/monthly aggregate  | Product mix can explain revenue, COGS, and margin movements.            | MEDIUM if computed from same-period realized sales.                      | Use lagged category mix or planned assortment/category indicators.                  |
| return_rate_lag_1m / return_rate_rolling_3m    | 06b_return_rate_monthly.csv | monthly                 | Return pressure can signal weak revenue quality and future margin risk. | LOW when lagged; HIGH if same-month full cohort return rate is used.     | Use lagged/rolling return metrics only.                                             |
| delivery_lead_days_lagged_summary              | orders, shipments, reviews  | order/monthly aggregate | Fulfillment delay may affect satisfaction and repeat demand.            | MEDIUM; same-order delivery outcome may not be known at forecast time.   | Use historical monthly averages or operational SLA features.                        |
| rating_lagged_average                          | reviews                     | monthly                 | Customer satisfaction trend can signal future demand and return risk.   | LOW when lagged; HIGH if using future reviews.                           | Use lagged average rating and review volume.                                        |

## Notes

- `sales.csv` is the source of daily Revenue/COGS.
- Item-level profit is estimated as `quantity * unit_price - discount_amount - quantity * products.cogs`.
- Traffic features should be lagged or rolling features computed only from past dates.
- Return-rate features should come from lagged/rolling values, not same-period future-complete cohorts.
- Correlation is directional guidance for feature exploration, not causal proof.
