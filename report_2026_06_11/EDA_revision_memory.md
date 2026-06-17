# EDA Revision Memory

## Mục tiêu chỉnh sửa
- Làm EDA dễ hiểu cho người mới, không ôm quá rộng.
- Mỗi phase chỉ trả lời đúng câu hỏi của phase đó.
- Không đẩy feature phức tạp lên quá sớm nếu chưa cần.
- Không kết luận mạnh khi Return Rate chỉ dao động nhẹ quanh baseline khoảng 6.5%.
- Tránh phân tích trùng giữa các phase.

## Nguyên tắc đã chốt
- `category` là đặc trưng sản phẩm, chỉ phân tích ở Phase 4, không phân tích ở Phase 2.
- Phase 2 chỉ là kiểm tra nhanh các biến số cơ bản với target.
- Các feature lịch sử phải tính bằng dữ liệu quá khứ trước đơn hiện tại, không dùng toàn bộ lịch sử vì dễ leakage.
- Feature phức tạp như `customer_cod_ratio`, `is_first_cod_order`, `days_since_last_order`, `product_age_days`, `order_hour` chưa đưa vào v1.
- Nếu có thêm feature nâng cao, ghi là Advanced/v2, không làm loãng luồng chính.

## Đã sửa

### Phase 0 - Setup & Tích hợp dữ liệu
- Sửa câu sai “merge vào `order_items`” thành merge vào `df_master`, lấy `orders` làm trung tâm.
- Bổ sung label audit:
  - `delivered`: 516,716 dòng.
  - `returned`: 36,142 dòng.
  - trạng thái khác / không dùng làm label: 94,087 dòng.
- Bổ sung shape audit:
  - trước drop label rỗng: `(714653, 35)`.
  - sau drop label rỗng: `(610906, 35)`.
- Bổ sung baseline Return Rate khoảng 6.54%.
- Sửa giọng văn “xử lý triệt để” thành “xử lý duplicate key để tránh nhân dòng sai khi merge”.

### Phase 2 - Bivariate nhanh với target
- Thêm `quantity`, `discount_amount` vào boxplot kiểm tra nhanh.
- Bỏ phân tích `category` khỏi Phase 2 vì đã thuộc Phase 4.
- Xóa cell notebook tạo `eda_phase2_return_rate_by_category`.
- Ghi rõ `quantity` và `discount_amount` chỉ check nhanh, phân tích kỹ ở Phase 6.
- Cần đổi layout boxplot Phase 2 thành 2 hàng x 2 cột để dễ nhìn.

Code layout Phase 2 cần dán vào cell boxplot:

```python
# So sánh sơ bộ biến số giữa nhóm Delivered (0) và Returned (1)
box_cols = ['unit_price', 'payment_value', 'quantity', 'discount_amount']
box_cols_exist = [c for c in box_cols if c in df_master.columns]

fig, axes = plt.subplots(2, 2, figsize=(14, 9))
axes = axes.flatten()

fig.suptitle(
    'So sánh sơ bộ các biến số theo label đơn hàng (Bivariate Analysis)',
    fontsize=14,
    fontweight='bold',
    y=1.02
)

for i, col in enumerate(box_cols_exist):
    ax = axes[i]
    sns.boxplot(
        data=df_master,
        x='returned_label',
        y=col,
        ax=ax,
        palette='coolwarm'
    )
    ax.set_title(f'Phân phối {col}', fontsize=11)
    ax.set_xlabel('')
    ax.set_ylabel(col)
    ax.set_xticklabels(['Delivered (0)', 'Returned (1)'])

for j in range(len(box_cols_exist), len(axes)):
    axes[j].axis('off')

plt.tight_layout()
output_p2_box = EDA_FIGURE_DIR / 'eda_phase2_numeric_vs_label.png'
fig.savefig(output_p2_box, dpi=150, bbox_inches='tight')
plt.show()

print(f'Da luu Boxplot phan tich luong bien: {output_p2_box}')
```

### Phase 4 - Product Features
- Đã cập nhật `2_EDA_task.md` để Phase 4 tập trung vào `category`, `segment`, `size`, `color`, SKU/product cụ thể và interaction nhẹ.
- Đã chỉnh notebook Phase 4:
  - Mục tiêu không còn chỉ nói `size` và `color`.
  - Trục x biểu đồ thuộc tính sản phẩm không còn cố định `0-0.4`; đã đổi sang giới hạn động để dễ nhìn hơn.
  - Sửa print message heatmap `gender × category`, không ghi nhầm thành `gender × size`.
  - Ghi rõ `product_historical_return_rate` và `is_high_return_product` là High / Advanced, chỉ dùng nếu tính bằng lịch sử quá khứ.
- Kết luận Phase 4 giữ thận trọng:
  - `category`, `segment`, `size`, `color` chỉ là Medium / Supporting.
  - interaction như `gender_category_interaction`, `category_size_interaction` là Low / Experimental.
  - tín hiệu mạnh hơn nằm ở cấp SKU/product, nhưng phải chống leakage.

## Cần sửa tiếp

### Phase 3 - Customer Profile
- Bỏ qua theo yêu cầu hiện tại của user.
- Không sửa Phase 3 nữa trong lượt chỉnh này.
- Ý tưởng “lịch sử trả hàng trước đó của khách” chỉ để Optional/Future, không đưa vào v1 nếu user không yêu cầu lại.

### Phase 5 - Payment, Device, Source
- Bỏ qua theo yêu cầu hiện tại của user.
- Không sửa Phase 5 trong lượt chỉnh này.
- Giữ COD là tín hiệu mạnh nhất.
- Không tạo riêng cờ cho từng giá trị của `device_type` hoặc `order_source` trong v1; giữ biến gốc `device_type`, `order_source` nếu cần supporting.
- `payment_device_interaction` để Low/Experimental nếu muốn giữ.
- Không thêm `customer_cod_ratio` hoặc `is_first_cod_order` ở v1 vì là feature lịch sử nâng cao.

### Phase 6 - Order Value, Quantity, Discount
- Đã sửa trong lượt này.
- Dùng quantile bucket cho `payment_value`, không dùng ngưỡng cố định kiểu `<50`, `50-200`, vì scale dữ liệu lớn.
- Thêm code tạo `is_discounted` và `discount_ratio = discount_amount / unit_price`.
- Đã lưu thêm:
  - `eda_phase6_return_rate_by_is_discounted.csv`
  - `eda_phase6_return_rate_by_discount_ratio.csv`
- Kết luận chính:
  - `payment_value` theo quantile chỉ lệch nhẹ khoảng 6.44%-6.69%.
  - `quantity` quanh 6.50%-6.63%, không có xu hướng rõ.
  - giảm giá chỉ lệch nhẹ: có giảm giá khoảng 6.57%, không giảm khoảng 6.54%; nhóm `discount_ratio` quanh 6.54%-6.61%.
- `price_vs_category_avg` để Optional/v2 vì phức tạp hơn và có thể làm rộng EDA.
- Kết luận thận trọng: order value, quantity, discount hiện chỉ có tín hiệu yếu.

### Phase 7 - Time & Seasonality
- Bỏ qua theo yêu cầu hiện tại của user.
- Không sửa Phase 7 trong lượt chỉnh này.
- Không thêm `order_hour` vì `orders.csv` chỉ có `order_date`, không có giờ.
- Không thêm `days_since_last_order` ở v1; nếu làm thì để Phase 3 hoặc Advanced customer history.
- Không kết luận Q4/weekend là driver mạnh nếu số liệu không ủng hộ.
- Calendar features chỉ Low/Experimental.

### Phase 8 - Feature Summary
- Đã sửa trong lượt này sau khi đối chiếu memory với output CSV đã chạy.
- Kết quả Phase 8 hiện tại:
  - 14 nhóm feature candidate.
  - High: 2 nhóm.
  - Medium: 6 nhóm.
  - Low/Experimental: 6 nhóm.
- Đồng bộ lại feature priority theo quyết định bỏ qua Phase 3 và các chỉnh sửa Phase 4.
- High chỉ nên gồm:
  - `is_cod`, `payment_method`
  - `product_historical_return_rate`, `is_high_return_product` nếu ghi rõ chống leakage / Advanced.
- Medium:
  - `customer_tenure_days`, `tenure_group`
  - prior customer history features nếu được thêm ở Phase 3
  - `category`, `segment`, `size`, `color`
  - `payment_value`, `log_payment_value`, quantile bucket
  - `quantity`, `discount_ratio`, `is_discounted`
- Low/Experimental:
  - age/gender
  - interactions
  - calendar flags
- Đã xác nhận bằng output:
  - COD khoảng 11.37%, các payment khác khoảng 5.8% -> High.
  - device/source gần baseline -> không High.
  - category/segment/size/color gần baseline -> Medium.
  - top SKU khoảng 10.7%-12.7% -> High / Advanced nếu chống leakage.
  - payment value, quantity, discount_ratio chỉ lệch nhẹ -> Medium.
  - calendar feature chỉ Low/Experimental.

## Các việc không làm trong v1
- Không tạo quá nhiều cross features.
- Không thêm feature không có dữ liệu gốc rõ ràng.
- Không dùng lịch sử toàn bộ dữ liệu để làm feature cho model.
- Không gọi feature là “mạnh” nếu EDA chỉ lệch vài phần trăm điểm rất nhỏ.
- Không phân tích cùng một biến ở nhiều phase nếu không có mục đích khác nhau rõ ràng.
