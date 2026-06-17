# Overview: Lộ trình xây dựng mô hình dự đoán đơn hàng bị trả lại

## 1. Mục tiêu bài toán

- Xây dựng mô hình classification để dự đoán đơn hàng có bị trả lại hay không.
- Nhãn dự đoán gồm Returned là 1 và Delivered là 0.
- Đây là bài toán phân loại nhị phân.
- Mục tiêu chính là hiểu quy trình huấn luyện mô hình từ dữ liệu đến đánh giá.
- Người mới cần nắm được các bước lớn trước khi đi vào code chi tiết.
- Kết quả cuối cùng là chọn được mô hình phù hợp cho bài toán.
- Sau phase này có thể chuẩn bị chuyển sang tracking experiment bằng MLflow.

## 2. Bối cảnh nghiệp vụ

- Doanh nghiệp có dữ liệu đơn hàng trong quá khứ.
- Một số đơn hàng đã giao thành công.
- Một số đơn hàng bị khách trả lại.
- Mô hình sẽ học từ dữ liệu cũ để dự đoán rủi ro trả hàng cho đơn mới.
- Nếu dự đoán tốt, doanh nghiệp có thể phát hiện sớm đơn hàng rủi ro cao.
- Kết quả mô hình có thể hỗ trợ vận hành, chăm sóc khách hàng và quản lý sản phẩm.
- Đây là bài toán thực tế thường gặp trong thương mại điện tử.

## 3. Các bảng dữ liệu sử dụng

- Bảng orders chứa thông tin tổng quan của đơn hàng.
- Bảng order_items chứa thông tin sản phẩm trong từng đơn hàng.
- Bảng customers chứa thông tin khách hàng.
- Bảng product_ids chứa thông tin định danh hoặc nhóm sản phẩm.
- Các bảng cần được kết nối lại để tạo dữ liệu huấn luyện.
- Dataset cuối cùng nên có một dòng đại diện cho một đơn hàng.
- Cần hiểu vai trò từng bảng trước khi xử lý dữ liệu.

## 4. Hiểu rõ nhãn dự đoán

- Nhãn là kết quả thật trong quá khứ mà mô hình cần học.
- Đơn hàng bị trả lại được gán nhãn 1.
- Đơn hàng giao thành công được gán nhãn 0.
- Cần kiểm tra nhãn có bị thiếu hoặc sai giá trị không.
- Cần đảm bảo nhãn được tạo nhất quán giữa các bảng.
- Không nên dùng thông tin chỉ xuất hiện sau khi đơn hàng đã bị trả lại.
- Nếu dùng nhầm thông tin tương lai, mô hình có thể tốt giả tạo nhưng không dùng được thực tế.

## 5. Hiểu bài toán classification

- Classification là bài toán dự đoán một lớp hoặc một nhóm.
- Trong bài này, mô hình chỉ dự đoán một trong hai lớp.
- Mô hình có thể trả về xác suất đơn hàng bị trả lại.
- Từ xác suất đó có thể chuyển thành nhãn 0 hoặc 1.
- Ngưỡng mặc định thường là 0.5 nhưng có thể điều chỉnh.
- Việc hiểu xác suất rất quan trọng khi đánh giá rủi ro.
- Đây là nền tảng để hiểu các metric như precision, recall và F1-score.

## 6. Kiểm tra chất lượng dữ liệu từng bảng

- Xem mỗi bảng có bao nhiêu dòng và bao nhiêu cột.
- Xem ý nghĩa cơ bản của từng cột trong từng bảng.
- Kiểm tra kiểu dữ liệu như số, chữ, ngày tháng và mã định danh.
- Kiểm tra dữ liệu thiếu ở từng cột.
- Kiểm tra dữ liệu trùng lặp trong từng bảng.
- Kiểm tra các giá trị bất thường như số âm, ngày sai hoặc giá trị rỗng.
- Mục tiêu của bước này là biết dữ liệu gốc có đáng tin cậy hay không.

## 7. Kiểm tra chất lượng dữ liệu sau khi nối bảng

- Xác định khóa chung giữa các bảng trước khi nối dữ liệu.
- Orders có thể nối với order_items qua mã đơn hàng.
- Orders có thể nối với customers qua mã khách hàng.
- Order_items có thể nối với product_ids qua mã sản phẩm.
- Sau khi nối bảng, cần kiểm tra số dòng có tăng hoặc giảm bất thường không.
- Cần tránh làm nhân bản đơn hàng sai cách khi một đơn có nhiều sản phẩm.
- Mục tiêu của bước này là đảm bảo dữ liệu sau khi join vẫn đúng logic.

## 8. EDA: Phân tích khám phá dữ liệu

- EDA giúp hiểu dữ liệu trước khi đưa vào mô hình.
- Cần xem tỷ lệ giữa Returned và Delivered.
- Cần xem phân phối của các feature dạng số như giá trị đơn hàng hoặc số lượng sản phẩm.
- Cần xem các nhóm khách hàng hoặc nhóm sản phẩm nào có tỷ lệ trả hàng cao.
- Cần quan sát mối quan hệ giữa feature và nhãn dự đoán.
- Cần phát hiện các pattern bất thường trong dữ liệu.
- Kết quả EDA giúp định hướng bước clean data và feature engineering.

## 9. Clean Data: Làm sạch dữ liệu

- Xử lý dữ liệu thiếu là bước cần làm trước khi huấn luyện.
- Với cột số, có thể thay bằng giá trị phù hợp.
- Với cột danh mục, có thể thay bằng nhóm Unknown.
- Cần xử lý giá trị không hợp lệ như số lượng âm hoặc ngày sai.
- Cần xử lý dòng trùng lặp nếu có.
- Cần chuẩn hóa định dạng dữ liệu như ngày tháng, mã đơn hàng và mã sản phẩm.
- Mọi quyết định làm sạch nên được ghi chú lại để dễ giải thích sau này.

## 10. Feature Engineering

- Feature engineering là quá trình tạo đặc trưng đầu vào cho mô hình.
- Feature có thể đến trực tiếp từ dữ liệu gốc.
- Feature cũng có thể được tạo thêm từ các bảng liên quan.
- Có thể tạo tổng số lượng sản phẩm trong đơn hàng.
- Có thể tạo tổng giá trị đơn hàng.
- Có thể tạo số loại sản phẩm khác nhau trong đơn.
- Nên bắt đầu với các feature đơn giản, dễ hiểu và có ý nghĩa nghiệp vụ.

## 11. Feature Selection

- Feature selection là bước chọn các feature phù hợp để đưa vào mô hình.
- Không phải feature nào có trong dữ liệu cũng nên sử dụng.
- Cần loại bỏ feature bị thiếu quá nhiều hoặc không có ý nghĩa rõ ràng.
- Cần loại bỏ feature có nguy cơ rò rỉ thông tin tương lai.
- Cần cân nhắc các feature có quá nhiều giá trị khác nhau.
- Có thể ưu tiên feature dễ giải thích trong phase đầu.
- Mục tiêu là giúp mô hình học tốt hơn và giảm nhiễu.

## 12. Xử lý feature số và feature danh mục

- Mô hình machine learning thường cần dữ liệu đầu vào ở dạng số.
- Feature danh mục cần được encode trước khi huấn luyện.
- One-hot encoding phù hợp với cột có ít giá trị khác nhau.
- Với cột có quá nhiều giá trị, cần cân nhắc cách xử lý phù hợp.
- Feature số cần kiểm tra giá trị bất thường trước khi dùng.
- Logistic Regression thường cần scale feature số.
- Các bước xử lý feature nên được áp dụng nhất quán giữa train, validation và test.

## 13. Xử lý nhãn mất cân bằng

- Trong thực tế, số đơn Delivered thường nhiều hơn Returned.
- Khi một lớp ít hơn nhiều, dữ liệu bị mất cân bằng.
- Nếu không xử lý, mô hình có thể chỉ dự đoán lớp phổ biến.
- Khi đó accuracy có thể cao nhưng khả năng phát hiện Returned lại thấp.
- Có thể dùng class weight, oversampling, undersampling hoặc điều chỉnh threshold.
- Cần chọn cách xử lý phù hợp với dữ liệu và mục tiêu đánh giá.
- Mục tiêu là giúp mô hình nhận diện tốt hơn các đơn hàng bị trả lại.

## 14. Chia train, validation và test

- Tập train dùng để huấn luyện mô hình.
- Tập validation dùng để thử nghiệm, so sánh và tuning.
- Tập test dùng để đánh giá cuối cùng.
- Không nên dùng tập test quá nhiều lần trong quá trình tuning.
- Khi dữ liệu mất cân bằng, nên giữ tỷ lệ nhãn tương đối giống nhau giữa các tập.
- Cách chia dữ liệu cần tránh làm rò rỉ thông tin giữa train và test.
- Chia dữ liệu đúng giúp đánh giá mô hình khách quan hơn.

## 15. Chọn baseline và metrics

- Baseline là mô hình đầu tiên dùng làm mốc so sánh.
- Logistic Regression thường là baseline tốt vì đơn giản và dễ hiểu.
- Cần chọn metric trước khi tuning mô hình.
- Accuracy cho biết tỷ lệ dự đoán đúng tổng thể.
- Precision cho biết trong các đơn dự đoán Returned, bao nhiêu đơn thật sự Returned.
- Recall cho biết trong các đơn thật sự Returned, mô hình phát hiện được bao nhiêu.
- Với bài toán mất cân bằng, nên xem thêm F1-score, ROC-AUC hoặc PR-AUC.

## 16. Train model lần đầu và đánh giá base

- Huấn luyện Logistic Regression để có kết quả baseline đầu tiên.
- Huấn luyện Random Forest để thử mô hình cây mạnh hơn baseline.
- Huấn luyện LightGBM để thử thuật toán boosting cho dữ liệu dạng bảng.
- Ở lần train đầu, chưa cần tuning quá nhiều.
- Mục tiêu là kiểm tra pipeline dữ liệu và model có chạy đúng không.
- Đánh giá cả ba mô hình bằng cùng tập validation và cùng metric.
- Ghi lại kết quả base để so sánh với các bước tuning sau này.

## 17. Tìm lỗi mô hình

- Sau khi có kết quả base, cần xem mô hình đang sai ở đâu.
- Cần xem confusion matrix để biết mô hình nhầm giữa Returned và Delivered như thế nào.
- Cần kiểm tra mô hình có bỏ sót quá nhiều đơn Returned không.
- Cần kiểm tra mô hình có báo nhầm quá nhiều đơn Delivered thành Returned không.
- Cần so sánh kết quả giữa train và validation để phát hiện overfitting.
- Nếu mô hình quá kém, cần quay lại xem dữ liệu, feature hoặc cách xử lý nhãn.
- Bước này giúp cải thiện mô hình có định hướng hơn.

## 18. Giải thích mô hình

- Giải thích mô hình giúp hiểu feature nào ảnh hưởng nhiều đến dự đoán.
- Với Logistic Regression, có thể xem hướng ảnh hưởng của các feature.
- Với Random Forest, có thể xem feature importance.
- Với LightGBM, cũng có thể xem feature importance.
- Cần kiểm tra các feature quan trọng có hợp lý về mặt nghiệp vụ không.
- Nếu feature quan trọng là thông tin không nên dùng, cần loại bỏ.
- Bước này giúp kết quả mô hình dễ trình bày và đáng tin hơn.

## 19. Tuning hyperparameters

- Tuning giúp tìm bộ tham số tốt hơn cho mô hình.
- Grid Search thử các tổ hợp tham số theo danh sách cố định.
- Random Search thử ngẫu nhiên các tổ hợp tham số để tiết kiệm thời gian hơn.
- Optuna tìm kiếm tham số thông minh hơn dựa trên các lần thử trước.
- Cần xác định metric mục tiêu trước khi tuning.
- Cần giới hạn phạm vi tuning để tránh chạy quá lâu.
- Sau tuning, cần so sánh lại với kết quả baseline ban đầu.

## 20. Chốt modeling

- Sau khi tuning, cần chọn mô hình phù hợp nhất với mục tiêu bài toán.
- Không nên chọn mô hình chỉ vì accuracy cao.
- Cần xem khả năng phát hiện đơn Returned.
- Cần xem mô hình có báo nhầm quá nhiều hay không.
- Cần xem mô hình có ổn định giữa train, validation và test không.
- Cần cân nhắc độ phức tạp và khả năng giải thích của mô hình.
- Mô hình được chọn nên là mô hình cân bằng giữa hiệu quả và tính thực tế.

## 21. Report kết quả

- Report cần tóm tắt mục tiêu bài toán và dữ liệu sử dụng.
- Report cần mô tả ngắn gọn các bước xử lý dữ liệu.
- Report cần nêu cách xử lý mất cân bằng nhãn.
- Report cần trình bày kết quả baseline và kết quả sau tuning.
- Report cần so sánh Logistic Regression, Random Forest và LightGBM.
- Report cần nêu mô hình được chọn và lý do chọn.
- Report có thể ghi chú phase tiếp theo là tracking experiment và registered model bằng MLflow.

