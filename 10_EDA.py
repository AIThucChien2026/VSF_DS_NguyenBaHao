"""

EDA — Hướng A: Revenue & Profit

=================================

Các bước:

  A1 — Xu hướng doanh thu (trend, seasonality, anomaly)

  A2 — Gross margin phân tích (theo category, segment, channel)

  A3 — AOV & order mix (phân phối giá trị đơn, single vs multi-item)

  A4 — Revenue by channel (order_source, device_type, payment_method)

  A5 — Revenue forecast check (reconcile sales.csv vs orders)
 

Yêu cầu: pandas, matplotlib, seaborn, scipy

Cấu trúc thư mục mặc định: tất cả file CSV cùng cấp với script này.

Có thể thay DATA_DIR để trỏ đến thư mục khác.

"""

 

import warnings

warnings.filterwarnings("ignore")

 

import os

import pandas as pd

import numpy as np

import matplotlib.pyplot as plt

import matplotlib.ticker as mticker

import seaborn as sns

from scipy import stats

 

# ─────────────────────────────────────────

# 0. CONFIG

# ─────────────────────────────────────────

DATA_DIR   = "."          # thư mục chứa CSV

OUTPUT_DIR = "output_A"   # thư mục lưu hình

os.makedirs(OUTPUT_DIR, exist_ok=True)

 

# Màu nhất quán cho toàn bộ hướng A

COLOR_PRIMARY   = "#534AB7"   # purple-600

COLOR_SECONDARY = "#1D9E75"   # teal-400

COLOR_ACCENT    = "#D85A30"   # coral-400

COLOR_NEUTRAL   = "#888780"   # gray-400

COLOR_WARN      = "#BA7517"   # amber-400

 

PALETTE_CAT = [COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT,

               COLOR_WARN, COLOR_NEUTRAL, "#D4537E", "#378ADD", "#639922"]

 

plt.rcParams.update({

    "figure.facecolor": "white",

    "axes.facecolor":   "white",

    "axes.spines.top":  False,

    "axes.spines.right":False,

    "axes.grid":        True,

    "grid.color":       "#E8E8E4",

    "grid.linewidth":   0.5,

    "font.size":        11,

    "axes.titlesize":   13,

    "axes.titleweight": "bold",

})

 

def savefig(name):

    path = os.path.join(OUTPUT_DIR, name)

    plt.savefig(path, dpi=150, bbox_inches="tight")

    plt.close()

    print(f"  saved → {path}")

 
 

# ─────────────────────────────────────────

# 1. LOAD DỮ LIỆU

# ─────────────────────────────────────────

print("=" * 55)

print("HƯỚNG A — REVENUE & PROFIT")

print("=" * 55)

 

print("\n[Load] Đọc dữ liệu...")

 

orders      = pd.read_csv(f"{DATA_DIR}/orders.csv",      parse_dates=["order_date"])

order_items = pd.read_csv(f"{DATA_DIR}/order_items.csv")

products    = pd.read_csv(f"{DATA_DIR}/products.csv")

payments    = pd.read_csv(f"{DATA_DIR}/payments.csv")

sales       = pd.read_csv(f"{DATA_DIR}/sales.csv",       parse_dates=["Date"])

 

print(f"  orders      : {orders.shape}")

print(f"  order_items : {order_items.shape}")

print(f"  products    : {products.shape}")

print(f"  payments    : {payments.shape}")

print(f"  sales       : {sales.shape}")

 
 

# ─────────────────────────────────────────

# 2. TIỀN XỬ LÝ

# ─────────────────────────────────────────

print("\n[Prep] Tính doanh thu dòng...")

 

# Doanh thu dòng = unit_price * quantity

order_items["line_revenue"] = order_items["unit_price"] * order_items["quantity"]

 

# Join order_items ← products để lấy category, segment, cogs

oi = order_items.merge(

    products[["product_id", "category", "segment", "cogs"]],

    on="product_id", how="left"

)

 

# Gross profit dòng = (unit_price - cogs) * quantity - discount_amount

oi["line_cogs"]   = oi["cogs"] * oi["quantity"]

oi["line_profit"] = (oi["unit_price"] - oi["cogs"]) * oi["quantity"] - oi["discount_amount"]

oi["line_margin"] = oi["line_profit"] / oi["line_revenue"].replace(0, np.nan)

 

# Join orders để lấy ngày, channel

oi = oi.merge(

    orders[["order_id", "order_date", "order_status",

            "order_source", "device_type", "payment_method"]],

    on="order_id", how="left"

)

 

# Bỏ đơn cancelled

oi_active = oi[oi["order_status"] != "cancelled"].copy()

 

# Thêm cột thời gian

oi_active["year"]       = oi_active["order_date"].dt.year

oi_active["month"]      = oi_active["order_date"].dt.to_period("M")

oi_active["week"]       = oi_active["order_date"].dt.to_period("W")

oi_active["dayofweek"]  = oi_active["order_date"].dt.day_name()

oi_active["quarter"]    = oi_active["order_date"].dt.to_period("Q")

 

print("  Tiền xử lý hoàn tất.")

 
 

# ─────────────────────────────────────────

# A1 — XU HƯỚNG DOANH THU

# ─────────────────────────────────────────

print("\n[A1] Xu hướng doanh thu...")

 

# --- A1-a: Daily revenue từ sales.csv với rolling average ---

sales_sorted = sales.sort_values("Date").copy()

sales_sorted["rolling_7"]  = sales_sorted["Revenue"].rolling(7,  min_periods=1).mean()

sales_sorted["rolling_30"] = sales_sorted["Revenue"].rolling(30, min_periods=1).mean()

 

fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})

 

ax = axes[0]

ax.fill_between(sales_sorted["Date"], sales_sorted["Revenue"],

                alpha=0.15, color=COLOR_PRIMARY)

ax.plot(sales_sorted["Date"], sales_sorted["Revenue"],

        lw=0.6, color=COLOR_PRIMARY, alpha=0.5, label="Daily revenue")

ax.plot(sales_sorted["Date"], sales_sorted["rolling_7"],

        lw=1.2, color=COLOR_ACCENT, label="7-day rolling avg")

ax.plot(sales_sorted["Date"], sales_sorted["rolling_30"],

        lw=2.0, color=COLOR_SECONDARY, label="30-day rolling avg")

ax.set_title("A1 — Daily Revenue Trend")

ax.set_ylabel("Revenue")

ax.legend(frameon=False)

ax.yaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

 

# Anomaly detection (Z-score > 3)

z = np.abs(stats.zscore(sales_sorted["Revenue"].fillna(0)))

anomalies = sales_sorted[z > 3]

if len(anomalies):

    ax.scatter(anomalies["Date"], anomalies["Revenue"],

               color=COLOR_WARN, zorder=5, s=40, label="Anomaly (z>3)")

    ax.legend(frameon=False)

 

# COGS vs Revenue (stacked area)

ax2 = axes[1]

ax2.fill_between(sales_sorted["Date"], sales_sorted["COGS"],

                 alpha=0.4, color=COLOR_ACCENT, label="COGS")

ax2.fill_between(sales_sorted["Date"],

                 sales_sorted["Revenue"] - sales_sorted["COGS"],

                 sales_sorted["COGS"],

                 alpha=0.3, color=COLOR_SECONDARY, label="Gross profit")

ax2.set_ylabel("Amount")

ax2.set_title("COGS vs Gross Profit (daily)")

ax2.legend(frameon=False, fontsize=9)

ax2.yaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

 

plt.tight_layout()

savefig("A1a_daily_revenue_trend.png")

 

# --- A1-b: Monthly revenue + YoY growth ---

monthly = oi_active.groupby("month").agg(

    revenue=("line_revenue", "sum"),

    profit=("line_profit", "sum"),

    orders=("order_id", "nunique"),

).reset_index()

monthly["month_dt"] = monthly["month"].dt.to_timestamp()

monthly["margin_pct"] = (monthly["profit"] / monthly["revenue"] * 100).round(1)

 

fig, ax = plt.subplots(figsize=(14, 5))

bars = ax.bar(monthly["month_dt"], monthly["revenue"],

              color=COLOR_PRIMARY, alpha=0.75, width=20, label="Revenue")

ax.plot(monthly["month_dt"], monthly["profit"],

        color=COLOR_SECONDARY, lw=2, marker="o", markersize=4, label="Gross profit")

ax.set_title("A1 — Monthly Revenue & Gross Profit")

ax.set_ylabel("Amount")

ax.legend(frameon=False)

ax.yaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

 

# Annotate margin % trên mỗi bar

for _, row in monthly.iterrows():

    ax.text(row["month_dt"], row["revenue"] * 1.01,

            f"{row['margin_pct']}%", ha="center", va="bottom",

            fontsize=8, color=COLOR_NEUTRAL)

 

plt.tight_layout()

savefig("A1b_monthly_revenue.png")

 

# --- A1-c: Heatmap doanh thu theo tháng x năm ---

monthly["year_val"]  = monthly["month"].dt.year

monthly["month_val"] = monthly["month"].dt.month

pivot_heatmap = monthly.pivot(index="year_val", columns="month_val", values="revenue")

 

fig, ax = plt.subplots(figsize=(14, max(3, len(pivot_heatmap) * 1.2)))

sns.heatmap(pivot_heatmap, annot=True, fmt=".0f", cmap="Purples",

            linewidths=0.5, ax=ax,

            cbar_kws={"label": "Revenue"})

ax.set_title("A1 — Revenue Heatmap (Year × Month)")

ax.set_xlabel("Month")

ax.set_ylabel("Year")

plt.tight_layout()

savefig("A1c_revenue_heatmap_yearmonth.png")

 

# --- A1-d: Day-of-week pattern ---

dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

dow = oi_active.groupby("dayofweek")["line_revenue"].sum().reindex(dow_order)

 

fig, ax = plt.subplots(figsize=(9, 4))

ax.bar(dow.index, dow.values, color=COLOR_PRIMARY, alpha=0.8)

ax.set_title("A1 — Revenue by Day of Week")

ax.set_ylabel("Total Revenue")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

plt.tight_layout()

savefig("A1d_revenue_dayofweek.png")

 

print(f"  Anomaly count (z>3): {len(anomalies)}")

print(f"  Monthly margin range: {monthly['margin_pct'].min()}% – {monthly['margin_pct'].max()}%")

 
 

# ─────────────────────────────────────────

# A2 — GROSS MARGIN PHÂN TÍCH

# ─────────────────────────────────────────

print("\n[A2] Gross margin theo nhóm...")

 

# --- A2-a: Margin theo category ---

cat_perf = oi_active.groupby("category").agg(

    revenue=("line_revenue", "sum"),

    profit=("line_profit", "sum"),

    units=("quantity", "sum"),

).reset_index()

cat_perf["margin_pct"] = (cat_perf["profit"] / cat_perf["revenue"] * 100).round(1)

cat_perf["revenue_share"] = (cat_perf["revenue"] / cat_perf["revenue"].sum() * 100).round(1)

cat_perf = cat_perf.sort_values("revenue", ascending=False)

 

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

 

# Revenue share (pie)

ax = axes[0]

wedges, texts, autotexts = ax.pie(

    cat_perf["revenue"], labels=cat_perf["category"],

    autopct="%1.1f%%", startangle=90,

    colors=PALETTE_CAT[:len(cat_perf)],

    pctdistance=0.8, wedgeprops={"linewidth": 0.5, "edgecolor": "white"}

)

for t in autotexts: t.set_fontsize(9)

ax.set_title("A2 — Revenue Share by Category")

 

# Margin % bar

ax = axes[1]

colors_bar = [COLOR_SECONDARY if m >= cat_perf["margin_pct"].median()

              else COLOR_ACCENT for m in cat_perf["margin_pct"]]

ax.barh(cat_perf["category"], cat_perf["margin_pct"], color=colors_bar, alpha=0.85)

ax.axvline(cat_perf["margin_pct"].median(), color=COLOR_NEUTRAL,

           lw=1.2, ls="--", label=f"Median {cat_perf['margin_pct'].median():.1f}%")

ax.set_xlabel("Gross Margin %")

ax.set_title("A2 — Gross Margin % by Category")

ax.legend(frameon=False)

for i, (val, cat) in enumerate(zip(cat_perf["margin_pct"], cat_perf["category"])):

    ax.text(val + 0.3, i, f"{val}%", va="center", fontsize=9)

 

plt.tight_layout()

savefig("A2a_margin_by_category.png")

 

# --- A2-b: Margin % theo segment x category (heatmap) ---

seg_cat = oi_active.groupby(["segment", "category"]).apply(

    lambda df: (df["line_profit"].sum() / df["line_revenue"].sum() * 100)

    if df["line_revenue"].sum() > 0 else 0

).reset_index(name="margin_pct")

pivot_seg = seg_cat.pivot(index="segment", columns="category", values="margin_pct")

 

fig, ax = plt.subplots(figsize=(max(8, pivot_seg.shape[1] * 1.5), max(4, pivot_seg.shape[0] * 0.9)))

sns.heatmap(pivot_seg.round(1), annot=True, fmt=".1f", cmap="RdYlGn",

            linewidths=0.5, ax=ax, center=pivot_seg.stack().median(),

            cbar_kws={"label": "Gross Margin %"})

ax.set_title("A2 — Gross Margin % Heatmap (Segment × Category)")

plt.tight_layout()

savefig("A2b_margin_heatmap_segment_category.png")

 

# --- A2-c: Quarterly margin trend by top-3 categories ---

top3_cats = cat_perf.head(3)["category"].tolist()

q_margin = (

    oi_active[oi_active["category"].isin(top3_cats)]

    .groupby(["quarter", "category"])

    .apply(lambda df: df["line_profit"].sum() / df["line_revenue"].sum() * 100

           if df["line_revenue"].sum() > 0 else 0)

    .reset_index(name="margin_pct")

)

q_margin["quarter_dt"] = q_margin["quarter"].dt.to_timestamp()

 

fig, ax = plt.subplots(figsize=(12, 4))

for i, cat in enumerate(top3_cats):

    sub = q_margin[q_margin["category"] == cat].sort_values("quarter_dt")

    ax.plot(sub["quarter_dt"], sub["margin_pct"],

            marker="o", lw=2, color=PALETTE_CAT[i], label=cat)

ax.set_title("A2 — Quarterly Margin Trend (Top 3 Categories)")

ax.set_ylabel("Gross Margin %")

ax.legend(frameon=False)

plt.tight_layout()

savefig("A2c_quarterly_margin_top3.png")

 

print("  Top categories by revenue:")

print(cat_perf[["category", "revenue", "margin_pct", "revenue_share"]].to_string(index=False))

 
 

# ─────────────────────────────────────────

# A3 — AOV & ORDER MIX

# ─────────────────────────────────────────

print("\n[A3] AOV & order mix...")

 

# Tổng hợp cấp độ đơn hàng

order_summary = (

    oi_active.groupby("order_id")

    .agg(

        order_revenue=("line_revenue", "sum"),

        order_profit=("line_profit", "sum"),

        total_items=("quantity", "sum"),

        distinct_products=("product_id", "nunique"),

        discount_total=("discount_amount", "sum"),

    )

    .reset_index()

)

order_summary["is_multiitem"] = order_summary["distinct_products"] > 1

order_summary["discount_rate"] = (

    order_summary["discount_total"] /

    (order_summary["order_revenue"] + order_summary["discount_total"])

    .replace(0, np.nan)

)

 

aov_overall = order_summary["order_revenue"].mean()

 

# --- A3-a: AOV distribution ---

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

 

ax = axes[0]

ax.hist(order_summary["order_revenue"].clip(upper=order_summary["order_revenue"].quantile(0.99)),

        bins=50, color=COLOR_PRIMARY, alpha=0.75, edgecolor="white")

ax.axvline(aov_overall, color=COLOR_ACCENT, lw=2, ls="--",

           label=f"AOV = {aov_overall:,.0f}")

ax.set_title("A3 — Order Value Distribution")

ax.set_xlabel("Order Revenue")

ax.set_ylabel("Count")

ax.legend(frameon=False)

ax.xaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e3:.0f}K" if x >= 1e3 else f"{x:.0f}"))

 

ax = axes[1]

single = order_summary[~order_summary["is_multiitem"]]["order_revenue"]

multi  = order_summary[order_summary["is_multiitem"]]["order_revenue"]

ax.hist(single.clip(upper=order_summary["order_revenue"].quantile(0.99)),

        bins=40, alpha=0.6, color=COLOR_PRIMARY, label=f"Single-product (n={len(single):,})")

ax.hist(multi.clip(upper=order_summary["order_revenue"].quantile(0.99)),

        bins=40, alpha=0.6, color=COLOR_SECONDARY, label=f"Multi-product (n={len(multi):,})")

ax.set_title("A3 — AOV: Single vs Multi-product Orders")

ax.set_xlabel("Order Revenue")

ax.set_ylabel("Count")

ax.legend(frameon=False)

plt.tight_layout()

savefig("A3a_aov_distribution.png")

 

# --- A3-b: AOV theo tháng ---

order_summary = order_summary.merge(

    orders[["order_id", "order_date"]], on="order_id", how="left"

)

order_summary["month"] = pd.to_datetime(order_summary["order_date"]).dt.to_period("M")

monthly_aov = order_summary.groupby("month").agg(

    aov=("order_revenue", "mean"),

    order_count=("order_id", "count"),

).reset_index()

monthly_aov["month_dt"] = monthly_aov["month"].dt.to_timestamp()

 

fig, ax = plt.subplots(figsize=(12, 4))

ax.plot(monthly_aov["month_dt"], monthly_aov["aov"],

        color=COLOR_PRIMARY, lw=2, marker="o", markersize=4)

ax.fill_between(monthly_aov["month_dt"], monthly_aov["aov"],

                alpha=0.1, color=COLOR_PRIMARY)

ax.axhline(aov_overall, color=COLOR_NEUTRAL, lw=1, ls="--",

           label=f"Overall AOV = {aov_overall:,.0f}")

ax.set_title("A3 — Monthly AOV Trend")

ax.set_ylabel("Average Order Value")

ax.legend(frameon=False)

plt.tight_layout()

savefig("A3b_monthly_aov.png")

 

# --- A3-c: Items per order distribution ---

fig, ax = plt.subplots(figsize=(9, 4))

val_counts = order_summary["distinct_products"].value_counts().sort_index()

ax.bar(val_counts.index.astype(str), val_counts.values,

       color=COLOR_PRIMARY, alpha=0.8, edgecolor="white")

ax.set_title("A3 — Distinct Products per Order")

ax.set_xlabel("Number of distinct products")

ax.set_ylabel("Order count")

for x, y in zip(range(len(val_counts)), val_counts.values):

    ax.text(x, y + val_counts.max() * 0.01, f"{y:,}", ha="center", fontsize=9)

plt.tight_layout()

savefig("A3c_items_per_order.png")

 

print(f"  Overall AOV: {aov_overall:,.0f}")

print(f"  Single-product orders: {(~order_summary['is_multiitem']).sum():,} "

      f"({(~order_summary['is_multiitem']).mean()*100:.1f}%)")

print(f"  Multi-product orders : {order_summary['is_multiitem'].sum():,} "

      f"({order_summary['is_multiitem'].mean()*100:.1f}%)")

 
 

# ─────────────────────────────────────────

# A4 — REVENUE BY CHANNEL

# ─────────────────────────────────────────

print("\n[A4] Revenue by channel...")

 

dims = [

    ("order_source",   "A4 — Revenue by Order Source"),

    ("device_type",    "A4 — Revenue by Device Type"),

    ("payment_method", "A4 — Revenue by Payment Method"),

]

 

fig, axes = plt.subplots(1, 3, figsize=(16, 5))

 

for ax, (dim, title) in zip(axes, dims):

    grp = (

        oi_active.groupby(dim)

        .agg(revenue=("line_revenue", "sum"),

             margin_pct=("line_profit", lambda x: x.sum() /

                         oi_active.loc[x.index, "line_revenue"].sum() * 100))

        .reset_index()

        .sort_values("revenue", ascending=True)

    )

    bars = ax.barh(grp[dim], grp["revenue"],

                   color=PALETTE_CAT[:len(grp)], alpha=0.85)

    ax.set_title(title, fontsize=11)

    ax.set_xlabel("Revenue")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(

        lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

    for i, (rev, mp) in enumerate(zip(grp["revenue"], grp["margin_pct"])):

        ax.text(rev * 1.01, i, f"{mp:.1f}%", va="center", fontsize=9,

                color=COLOR_NEUTRAL)

    ax.text(0.98, 0.02, "margin %", transform=ax.transAxes,

            ha="right", va="bottom", fontsize=8, color=COLOR_NEUTRAL)

 

plt.suptitle("A4 — Revenue & Margin by Channel Dimensions", fontsize=13, fontweight="bold", y=1.01)

plt.tight_layout()

savefig("A4_revenue_by_channel.png")

 

# --- A4-b: Channel share trend over quarters ---

q_channel = (

    oi_active.groupby(["quarter", "order_source"])["line_revenue"]

    .sum().reset_index()

)

q_channel["quarter_dt"] = q_channel["quarter"].dt.to_timestamp()

pivot_ch = q_channel.pivot(index="quarter_dt", columns="order_source", values="line_revenue").fillna(0)

pivot_ch_pct = pivot_ch.div(pivot_ch.sum(axis=1), axis=0) * 100

 

fig, ax = plt.subplots(figsize=(12, 5))

pivot_ch_pct.plot(kind="area", stacked=True, ax=ax,

                  color=PALETTE_CAT[:len(pivot_ch_pct.columns)], alpha=0.75)

ax.set_title("A4 — Order Source Share Trend (Quarterly)")

ax.set_ylabel("Revenue Share %")

ax.set_xlabel("")

ax.legend(frameon=False, loc="upper left", fontsize=9)

plt.tight_layout()

savefig("A4b_channel_share_trend.png")

 

print("  Revenue by order_source:")

src_sum = oi_active.groupby("order_source")["line_revenue"].sum().sort_values(ascending=False)

for k, v in src_sum.items():

    pct = v / src_sum.sum() * 100

    print(f"    {k:<20} {v:>12,.0f}  ({pct:.1f}%)")

 
 

# ─────────────────────────────────────────

# A5 — REVENUE FORECAST CHECK (RECONCILE)

# ─────────────────────────────────────────

print("\n[A5] Reconcile sales.csv vs orders...")

 

# Tổng hợp doanh thu ngày từ order_items

daily_calc = (

    oi_active.groupby("order_date")

    .agg(

        calc_revenue=("line_revenue", "sum"),

        calc_cogs=("line_cogs", "sum"),

    )

    .reset_index()

    .rename(columns={"order_date": "Date"})

)

 

reconcile = sales_sorted.merge(daily_calc, on="Date", how="outer")

reconcile = reconcile.sort_values("Date")

reconcile["revenue_diff"]   = reconcile["Revenue"] - reconcile["calc_revenue"]

reconcile["cogs_diff"]      = reconcile["COGS"]    - reconcile["calc_cogs"]

reconcile["diff_pct_rev"]   = (reconcile["revenue_diff"] /

                                reconcile["Revenue"].replace(0, np.nan) * 100)

 

# Thống kê

match_days = (reconcile["diff_pct_rev"].abs() <= 1).sum()

total_days  = reconcile.dropna(subset=["Revenue", "calc_revenue"]).shape[0]

 

fig, axes = plt.subplots(2, 1, figsize=(14, 7))

 

ax = axes[0]

ax.plot(reconcile["Date"], reconcile["Revenue"],

        lw=1.5, color=COLOR_PRIMARY, label="sales.csv Revenue", alpha=0.8)

ax.plot(reconcile["Date"], reconcile["calc_revenue"],

        lw=1.5, color=COLOR_SECONDARY, ls="--", label="Calculated from orders", alpha=0.8)

ax.set_title("A5 — Revenue Reconciliation: sales.csv vs Calculated")

ax.set_ylabel("Revenue")

ax.legend(frameon=False)

ax.yaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

 

ax = axes[1]

ax.bar(reconcile["Date"], reconcile["revenue_diff"],

       color=[COLOR_ACCENT if d > 0 else COLOR_SECONDARY

              for d in reconcile["revenue_diff"].fillna(0)],

       alpha=0.7, width=1)

ax.axhline(0, color=COLOR_NEUTRAL, lw=0.8)

ax.set_title("A5 — Daily Revenue Gap (sales.csv − Calculated)")

ax.set_ylabel("Difference")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(

    lambda x, _: f"{x/1e3:.0f}K"))

 

plt.tight_layout()

savefig("A5_revenue_reconcile.png")

 

# --- Scatter: sales.csv vs calc ---

both = reconcile.dropna(subset=["Revenue", "calc_revenue"])

fig, ax = plt.subplots(figsize=(7, 6))

ax.scatter(both["calc_revenue"], both["Revenue"],

           alpha=0.4, s=15, color=COLOR_PRIMARY)

lim_max = max(both["Revenue"].max(), both["calc_revenue"].max()) * 1.05

ax.plot([0, lim_max], [0, lim_max], color=COLOR_ACCENT, lw=1.5, ls="--", label="Perfect match")

ax.set_xlabel("Calculated Revenue (from orders)")

ax.set_ylabel("sales.csv Revenue")

ax.set_title("A5 — Scatter: sales.csv vs Calculated Revenue")

ax.legend(frameon=False)

corr = both["Revenue"].corr(both["calc_revenue"])

ax.text(0.05, 0.95, f"Pearson r = {corr:.4f}",

        transform=ax.transAxes, va="top", fontsize=10)

plt.tight_layout()

savefig("A5b_reconcile_scatter.png")

 

print(f"  Days with <1% diff : {match_days}/{total_days} ({match_days/total_days*100:.1f}%)")

print(f"  Avg revenue diff   : {reconcile['revenue_diff'].mean():,.0f}")

print(f"  Max revenue diff   : {reconcile['revenue_diff'].abs().max():,.0f}")

print(f"  Pearson r          : {corr:.4f}")

 
 

# ─────────────────────────────────────────

# SUMMARY TABLE

# ─────────────────────────────────────────

print("\n" + "=" * 55)

print("SUMMARY — HƯỚNG A")

print("=" * 55)

 

total_rev    = oi_active["line_revenue"].sum()

total_profit = oi_active["line_profit"].sum()

overall_margin = total_profit / total_rev * 100 if total_rev > 0 else 0

 

summary = pd.DataFrame({

    "Metric": [

        "Total Revenue (active orders)",

        "Total Gross Profit",

        "Overall Gross Margin %",

        "Average Order Value (AOV)",

        "Total Active Orders",

        "Multi-product order rate",

        "Anomaly days (revenue z>3)",

    ],

    "Value": [

        f"{total_rev:,.0f}",

        f"{total_profit:,.0f}",

        f"{overall_margin:.2f}%",

        f"{aov_overall:,.0f}",

        f"{order_summary['order_id'].nunique():,}",

        f"{order_summary['is_multiitem'].mean()*100:.1f}%",

        f"{len(anomalies)}",

    ]

})

print(summary.to_string(index=False))

 

print(f"\nTất cả biểu đồ đã được lưu vào thư mục: ./{OUTPUT_DIR}/")

print("  A1a_daily_revenue_trend.png")

print("  A1b_monthly_revenue.png")

print("  A1c_revenue_heatmap_yearmonth.png")

print("  A1d_revenue_dayofweek.png")

print("  A2a_margin_by_category.png")

print("  A2b_margin_heatmap_segment_category.png")

print("  A2c_quarterly_margin_top3.png")

print("  A3a_aov_distribution.png")

print("  A3b_monthly_aov.png")

print("  A3c_items_per_order.png")

print("  A4_revenue_by_channel.png")

print("  A4b_channel_share_trend.png")

print("  A5_revenue_reconcile.png")

print("  A5b_reconcile_scatter.png")

 
 
 