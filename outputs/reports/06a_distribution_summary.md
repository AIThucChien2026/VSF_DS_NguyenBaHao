# Distribution Analysis (06a)

## Overview

| Metric | Value |
|---|---:|
| Numeric fields summarized | 24 |
| Categorical top-value rows | 81 |
| Strongly skewed numeric fields | 15 |
| Numeric fields with >20% zero values | 2 |

## Revenue Distribution Shape

|        mean |     median |         p95 |        p99 |         max |   skew |   mean_median_gap_pct |
|------------:|-----------:|------------:|-----------:|------------:|-------:|----------------------:|
| 4.28658e+06 | 3.6473e+06 | 9.39876e+06 | 1.3802e+07 | 2.09053e+07 |   1.67 |                17.527 |

## Top Revenue Groups - Order and Customer Level

| analysis_level   | group_field    | group_value    |     revenue |   revenue_pct |   orders |
|:-----------------|:---------------|:---------------|------------:|--------------:|---------:|
| customer_level   | age_group      | 25-34          | 4.63001e+09 |       29.5265 |   190622 |
| customer_level   | age_group      | 35-44          | 4.12628e+09 |       26.3141 |   170368 |
| customer_level   | age_group      | 45-54          | 3.01938e+09 |       19.2552 |   124138 |
| order_level      | device_type    | mobile         | 7.06679e+09 |       45.0663 |   291482 |
| order_level      | device_type    | desktop        | 6.26504e+09 |       39.9534 |   258855 |
| order_level      | device_type    | tablet         | 2.34904e+09 |       14.9803 |    96608 |
| order_level      | order_source   | organic_search | 4.38532e+09 |       27.9661 |   181495 |
| order_level      | order_source   | paid_search    | 3.44196e+09 |       21.9501 |   141652 |
| order_level      | order_source   | social_media   | 3.14115e+09 |       20.0318 |   129710 |
| order_level      | payment_method | credit_card    | 8.63007e+09 |       55.0357 |   356352 |
| order_level      | payment_method | paypal         | 2.36368e+09 |       15.0737 |    97018 |
| order_level      | payment_method | cod            | 2.34695e+09 |       14.9669 |    96681 |

## Top Revenue Groups - Product Item Level

| group_field   | group_value       |     revenue |   revenue_pct |   item_rows |   quantity |
|:--------------|:------------------|------------:|--------------:|------------:|-----------:|
| category      | Streetwear        | 1.25585e+10 |      80.0879  |      393533 |    1768826 |
| category      | Outdoor           | 2.3534e+09  |      15.0081  |      259986 |    1170000 |
| category      | Casual            | 4.40285e+08 |       2.80779 |       23991 |     107469 |
| category      | GenZ              | 3.2871e+08  |       2.09625 |       37159 |     166848 |
| product_name  | SaigonFlex UM-92  | 3.80469e+08 |       2.42632 |        7418 |      33277 |
| product_name  | HanoiStreet UM-10 | 3.27509e+08 |       2.08859 |        6422 |      28993 |
| product_name  | SaigonFlex UM-43  | 3.25015e+08 |       2.07268 |        7053 |      31471 |
| product_name  | SaigonFlex UM-01  | 2.98101e+08 |       1.90105 |        6690 |      30088 |
| product_name  | SaigonFlex UM-80  | 2.56552e+08 |       1.63608 |        4982 |      22709 |
| segment       | Everyday          | 5.14745e+09 |      32.8263  |      182533 |     819449 |
| segment       | Balanced          | 4.90032e+09 |      31.2503  |      103333 |     464217 |
| segment       | Performance       | 2.28503e+09 |      14.5721  |       96730 |     435685 |
| segment       | Activewear        | 1.9307e+09  |      12.3125  |      230375 |    1036857 |
| segment       | Premium           | 4.54212e+08 |       2.8966  |       31032 |     139465 |

## Strong Skew Candidates

| table       | column          |    skew | skew_flag           |            mean |          median |
|:------------|:----------------|--------:|:--------------------|----------------:|----------------:|
| sales       | Revenue         |  1.67   | right_skewed_strong |     4.28658e+06 |     3.6473e+06  |
| sales       | COGS            |  1.6251 | right_skewed_strong |     3.69513e+06 |     3.16111e+06 |
| sales       | Margin          | -2.5316 | left_skewed_strong  |     0.1254      |     0.1783      |
| payments    | payment_value   |  1.6791 | right_skewed_strong | 24238.3         | 17229.4         |
| payments    | installments    |  1.6189 | right_skewed_strong |     3.4483      |     3           |
| order_items | unit_price      |  1.016  | right_skewed_strong |  5114.69        |  4257.77        |
| order_items | discount_amount |  3.3825 | right_skewed_strong |  1048.89        |     0           |
| products    | price           |  1.33   | right_skewed_strong |  4928.22        |  4399.6         |
| products    | cogs            |  1.4879 | right_skewed_strong |  3868.35        |  3184.93        |
| returns     | refund_amount   |  2.3195 | right_skewed_strong | 12784.5         |  7888.88        |
| inventory   | stock_on_hand   |  3.2152 | right_skewed_strong |   189.298       |    62           |
| inventory   | units_sold      |  5.5466 | right_skewed_strong |    15.4178      |     6           |

## High Zero-Value Candidates

| table       | column          |   zero_pct |      mean |   median |
|:------------|:----------------|-----------:|----------:|---------:|
| order_items | discount_amount |     61.337 | 1048.89   |        0 |
| inventory   | stockout_days   |     32.659 |    1.1606 |        1 |

## Dominant Categorical Values

| table       | column              | value          |    pct |   unique_values |
|:------------|:--------------------|:---------------|-------:|----------------:|
| orders      | order_status        | delivered      | 79.87  |               6 |
| orders      | payment_method      | credit_card    | 55.082 |               5 |
| products    | category            | Streetwear     | 54.726 |               4 |
| customers   | gender              | Female         | 48.913 |               3 |
| orders      | device_type         | mobile         | 45.055 |               3 |
| returns     | return_reason       | wrong_size     | 34.971 |               5 |
| customers   | acquisition_channel | organic_search | 29.894 |               6 |
| web_traffic | traffic_source      | organic_search | 29.847 |               6 |
| customers   | age_group           | 25-34          | 29.806 |               5 |
| orders      | order_source        | organic_search | 28.054 |               6 |
| products    | size                | S              | 25     |               4 |
| products    | segment             | Activewear     | 24.793 |               8 |

## Notes

- This step describes distributions only; it does not infer causality.
- `sales` includes derived `Gross Profit = Revenue - COGS` and `Margin = Gross Profit / Revenue`.
- Revenue by order/customer groups uses a focused `orders` + order-level `payments` merge.
- Revenue by product groups uses a focused `order_items` + `products` merge and `quantity * unit_price - discount_amount`.
- Detailed outputs are saved in `06a_numeric_describe.csv`, `06a_categorical_top_values.csv`, `06a_revenue_by_order_group.csv`, and `06a_revenue_by_product_group.csv`.
