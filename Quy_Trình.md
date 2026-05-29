# QUY TRÌNH PHÂN TÍCH DỮ LIỆU CHI TIẾT THEO CHUẨN CRISP-DM

Bản tóm tắt chi tiết và toàn diện về quy trình *CRISP-DM (Cross-Industry Standard Process for Data Mining)* dựa trên tài liệu hướng dẫn chuẩn của IBM SPSS Modeler. Mỗi giai đoạn được cấu trúc chặt chẽ gồm: **Mục tiêu**, **Các công việc cụ thể phải làm (Tasks)**, và **Điều kiện tiên quyết / Câu hỏi chiến lược cần trả lời (Deliverables)** nhằm đảm bảo chất lượng cao nhất trước khi bước sang giai đoạn tiếp theo.

---

## GIAI ĐOẠN 1: THẤU HIỂU DOANH NGHIỆP (BUSINESS UNDERSTANDING)

Giai đoạn này tập trung vào việc tìm hiểu các mục tiêu và yêu cầu của dự án dưới góc độ kinh doanh, sau đó chuyển đổi các kiến thức này thành một định nghĩa bài toán khai phá dữ liệu cụ thể và lập kế hoạch thực hiện.

### 1. Các công việc cần làm (Tasks)

* **Xác định mục tiêu kinh doanh (Determine Business Objectives):** Tìm hiểu bối cảnh, cấu trúc tổ chức, xác định các bên liên quan (sponsors, đơn vị chịu ảnh hưởng), mô tả vùng bài toán và giải pháp hiện tại (nêu rõ ưu/nhược điểm). Cụ thể hóa các câu hỏi kinh doanh và lợi ích kỳ vọng.
* **Đánh giá tình hình hiện tại (Assess the Situation):** Kiểm kê tài nguyên bao gồm phần cứng, nguồn dữ liệu hiện có (định dạng, vị trí, bảo mật), và nhân sự chuyên trách. Xác định các ràng buộc (pháp lý, ngân sách, bảo mật), các giả định kinh doanh/kỹ thuật, rủi ro và xây dựng phương án dự phòng cho từng rủi ro.
* **Xác định mục tiêu Khai phá Dữ liệu (Determine Data Mining Goals):** Dịch bài toán kinh doanh thành bài toán kỹ thuật dữ liệu (ví dụ: chuyển đổi từ "giảm tỷ lệ rời bỏ của khách hàng" thành bài toán phân lớp, phân cụm hoặc dự đoán xác suất rời bỏ kèm theo khung thời gian hiệu lực cụ thể).
* **Lập kế hoạch dự án (Produce a Project Plan):** Xây dựng lộ trình tổng thể, ước tính thời gian và nguồn lực cho từng giai đoạn, đánh giá và lựa chọn công cụ/kỹ thuật phù hợp.

### 2. Các câu hỏi cần trả lời trước khi chuyển sang bước tiếp theo

Để chắc chắn đã hoàn thành giai đoạn này, toàn bộ đội ngũ phải trả lời *"CÓ"* cho các câu hỏi sau:

1. Doanh nghiệp thực sự kỳ vọng đạt được điều gì từ dự án này?
2. Tiêu chí thành công của dự án được định nghĩa chính xác dưới góc độ kinh doanh (ví dụ: tăng doanh thu 10%, giảm chi phí...) và góc độ kỹ thuật (độ chính xác, thời gian phản hồi...) là gì?
3. Dự án đã có đủ ngân sách, tài nguyên phần cứng và quyền truy cập vào tất cả các nguồn dữ liệu cần thiết chưa?
4. Toàn bộ các rủi ro cốt lõi (về lịch trình, tài chính, dữ liệu) và phương án dự phòng tương ứng đã được thảo luận và ký duyệt chưa?
5. Kết quả phân tích Chi phí / Lợi ích (Cost/Benefit Analysis) có chứng minh dự án này xứng đáng để đầu tư không?
6. Bạn đã có định hướng cụ thể về kỹ thuật khai phá dữ liệu nào có khả năng mang lại kết quả tốt nhất chưa?
7. Mô hình sau khi hoàn thiện sẽ được triển khai như thế nào (Đưa lên Web, ghi vào kho dữ liệu...)? Yêu cầu triển khai này đã được tích hợp vào kế hoạch dự án chưa?

---

## GIAI ĐOẠN 2: THẤU HIỂU DỮ LIỆU (DATA UNDERSTANDING)

Giai đoạn này bắt đầu bằng việc thu thập dữ liệu ban đầu và tiếp tục bằng các hoạt động nhằm làm quen với dữ liệu, xác định các vấn đề về chất lượng dữ liệu, khám phá những thông tin chi tiết đầu tiên hoặc phát hiện các tập con thú vị.

### 1. Các công việc cần làm (Tasks)

* **Thu thập dữ liệu ban đầu (Collect Initial Data):** Tiến hành nạp dữ liệu từ các nguồn đã xác định và lập báo cáo thu thập dữ liệu (nêu rõ các vướng mắc nếu có).
* **Mô tả dữ liệu (Describe Data):** Kiểm tra các thuộc tính bề mặt của dữ liệu bao gồm: lượng dữ liệu (số lượng bản ghi, số trường), kiểu giá trị (số, phân loại, Boolean), hệ thống mã hóa dữ liệu (ví dụ: M/F hay 1/2) và viết Báo cáo mô tả dữ liệu.
* **Khám phá dữ liệu (Explore Data):** Sử dụng các truy vấn cơ bản, kỹ thuật thống kê mô tả và biểu đồ trực quan hóa để tìm kiếm các mối quan hệ, mô hình phân phối hoặc kiểm tra các giả thuyết ban đầu. Lập Báo cáo khám phá dữ liệu.
* **Xác minh chất lượng dữ liệu (Verify Data Quality):** Đánh giá mức độ hoàn thiện và sạch sẽ của dữ liệu. Nhận diện các lỗi: dữ liệu bị thiếu (missing value), lỗi gõ phím/nhập liệu, lỗi đo lường, sự bất nhất trong mã hóa, hoặc siêu dữ liệu (metadata) sai lệch. Lập Báo cáo chất lượng dữ liệu.

### 2. Các câu hỏi cần trả lời trước khi chuyển sang bước tiếp theo

Trước khi tiến hành tiền xử lý, hãy đảm bảo các điểm sau đã sáng tỏ:

1. Bạn đã xác định rõ và có thể truy cập thành công vào tất cả các nguồn dữ liệu chưa? Có rào cản hay hạn chế pháp lý nào phát sinh không?
2. Các thuộc tính quan trọng (key attributes) định hình cho bài toán đã được xác định chưa? Chúng có giúp bạn hình thành hay điều chỉnh các giả thuyết nghiên cứu nào không?
3. Bạn đã nắm rõ kích thước của tất cả các nguồn dữ liệu chưa? Việc sử dụng một tập con (subset) dữ liệu để tối ưu thời gian xử lý có khả thi không?
4. Các chỉ số thống kê cơ bản và đồ thị khám phá dữ liệu có hé lộ bất kỳ thông tin bất thường hay xung đột logic nào không (ví dụ: độ tuổi thiếu niên nhưng thu nhập rất cao)?
5. Các vấn đề về chất lượng dữ liệu (thiếu, sai, không nhất quán) cụ thể của dự án là gì? Bạn đã có kế hoạch hoặc phương pháp để xử lý chúng chưa?
6. Các bước chuẩn bị dữ liệu tiếp theo đã rõ ràng chưa (biết rõ nguồn nào cần gộp, thuộc tính nào cần lọc bỏ hoặc giữ lại)?

---

## GIAI ĐOẠN 3: CHUẨN BỊ DỮ LIỆU (DATA PREPARATION)

Giai đoạn này bao gồm tất cả các hoạt động để xây dựng tập dữ liệu cuối cùng (dữ liệu sẽ được đưa vào công cụ mô hình hóa) từ dữ liệu thô ban đầu. Nhiệm vụ này thường chiếm từ 50% đến 70% toàn bộ thời gian và công sức của dự án.

### 1. Các công việc cần làm (Tasks)

* **Lựa chọn dữ liệu (Select Data):** Quyết định các tập dữ liệu sẽ được sử dụng và lý do lựa chọn/loại bỏ (dựa trên mức độ liên quan đến mục tiêu, chất lượng dữ liệu hoặc các ràng buộc kỹ thuật). Lựa chọn các dòng (bản ghi) và các cột (thuộc tính) cần thiết.
* **Làm sạch dữ liệu (Clean Data):** Thực hiện các kỹ thuật xử lý dữ liệu bẩn để nâng cấp chất lượng dữ liệu đạt yêu cầu của công cụ mô hình hóa (như điền giá trị thiếu, xử lý nhiễu, chuẩn hóa các chuỗi bất nhất). Viết Báo cáo làm sạch dữ liệu.
* **Xây dựng dữ liệu mới (Construct New Data):** Tạo ra các thuộc tính phái sinh mới từ các trường có sẵn nhằm tăng cường sức mạnh dự báo (ví dụ: từ ngày sinh tính ra tuổi, từ log truy cập tính tổng thời gian online...) hoặc tạo ra các bản ghi mới.
* **Tích hợp dữ liệu (Integrate Data):** Kết hợp thông tin từ nhiều bảng/nguồn khác nhau thông qua các thao tác: Trộn dữ liệu (Merge - tăng thêm số cột dựa trên Key như Customer ID) hoặc Nối dữ liệu (Append - tăng thêm số dòng từ các bảng có cấu trúc tương tự). Thực hiện tổng hợp dữ liệu (Aggregation) nếu cần.
* **Định dạng lại dữ liệu (Format Data):** Thay đổi cấu trúc hoặc định dạng hiển thị của dữ liệu mà không làm thay đổi ý nghĩa của nó để phù hợp với thuật toán (ví dụ: chuyển chuỗi thành số, chuyển bảng dọc thành bảng ngang).

### 2. Các câu hỏi cần trả lời trước khi chuyển sang bước tiếp theo

Để chắc chắn dữ liệu đã sẵn sàng cho giai đoạn Modeling, bạn cần trả lời được:

1. Tập dữ liệu cuối cùng đã được lưu trữ dưới cấu trúc tối ưu (ví dụ: flat files với dấu phân cách nhất quán, số lượng trường đồng đều trên mỗi bản ghi) chưa?
2. Các thuộc tính nhiễu hoặc không có đóng góp gì cho giả thuyết bài toán đã được lọc bỏ hoàn toàn chưa?
3. Các kỹ thuật làm sạch dữ liệu có làm sai lệch phân phối tự nhiên của dữ liệu gốc hay không?
4. Các phép tích hợp dữ liệu (Merge/Append) đã được kiểm tra lại qua một quy trình khám phá ngắn để đảm bảo không bị trùng lặp hay mất mát bản ghi chưa?

---

## GIAI ĐOẠN 4: MÔ HÌNH HÓA (MODELING)

Trong giai đoạn này, các kỹ thuật mô hình hóa khác nhau được lựa chọn và áp dụng, đồng thời các tham số của chúng được tinh chỉnh về giá trị tối ưu.

### 1. Các công việc cần làm (Tasks)

* **Lựa chọn kỹ thuật mô hình hóa (Select Modeling Technique):** Xác định chính xác thuật toán sẽ sử dụng (ví dụ: C5.0 cho phân lớp, Kohonen cho phân cụm). Ghi nhận lại các giả định (assumptions) mà thuật toán đó yêu cầu đối với dữ liệu.
* **Tạo thiết kế kiểm thử (Generate Test Design):** Xây dựng cơ chế để kiểm tra tính hiệu quả của mô hình. Thông thường là phân chia dữ liệu thành các tập Train (huấn luyện) và Test (kiểm thử).
* **Xây dựng mô hình (Build Model):** Chạy thuật toán trên tập dữ liệu chuẩn bị. Thiết lập và ghi lại các thông số tham số (parameter settings) ban đầu. Tạo ra bản mô tả chi tiết về cấu trúc mô hình thu được.
* **Đánh giá mô hình (Assess Model):** Đánh giá mô hình dựa trên các tiêu chí kỹ thuật dữ liệu (độ chính xác, ma trận nhầm lẫn, biểu đồ nâng số - gains chart). Ghi lại nhật ký điều chỉnh tham số qua các vòng lặp.

### 2. Các câu hỏi cần trả lời trước khi chuyển sang bước tiếp theo

Mô hình hóa là một quy trình lặp đi lặp lại rất cao, bạn chỉ được dừng lại để bước sang giai đoạn Evaluation khi trả lời được các câu hỏi sau:

1. Bạn đã phân chia dữ liệu Train/Test một cách hợp lý và khách quan chưa?
2. Bạn đã thiết lập cơ chế đo lường thành công cụ thể cho từng loại mô hình (giám sát hay không giám sát) chưa?
3. Bạn đã xác định rõ giới hạn số lần thử nghiệm điều chỉnh tham số cho một thuật toán trước khi quyết định từ bỏ để chuyển sang một dạng mô hình khác chưa?
4. Mô hình tạo ra có đáp ứng được các tiêu chí kỹ thuật và mục tiêu khai phá dữ liệu đã đặt ra ở Giai đoạn 1 không?
5. Kết quả của mô hình có khả thi để triển khai trong thực tế (Ví dụ: tổ chức yêu cầu triển khai trên nền tảng Web hay đẩy về kho dữ liệu, mô hình hiện tại có tương thích không)?

---

## GIAI ĐOẠN 5: ĐÁNH GIÁ (EVALUATION)

Trước khi tiến hành triển khai chính thức mô hình, điều quan trọng là phải đánh giá kỹ lưỡng mô hình và xem xét quy trình đã thực hiện để đảm bảo mô hình đạt được các mục tiêu kinh doanh một cách chính xác.

### 1. Các công việc cần làm (Tasks)

* **Đánh giá kết quả (Evaluate Results):** Đối chiếu các kết quả kỹ thuật thu được từ mô hình (bao gồm cả các phát hiện phụ - findings) với các tiêu chí thành công của doanh nghiệp đặt ra ở đầu dự án. Đưa các nhà ra quyết định (key decision makers) vào cùng đánh giá.
* **Xem xét lại quy trình (Review Process):** Nhìn nhận lại toàn bộ các hoạt động đã qua ở tất cả các giai đoạn. Phân tích xem có giai đoạn nào bị bỏ sót lỗi không, có lỗi lầm/ngõ cụt nào có thể rút kinh nghiệm để tối ưu hóa quy trình cho các dự án sau không.
* **Xác định các bước tiếp theo (Determine Next Steps):** Dựa trên kết quả đánh giá, đưa ra quyết định tối cao: Di chuyển tiếp sang giai đoạn Triển khai (Deployment) hay quay trở lại các bước trước (ví dụ: Chuẩn bị dữ liệu hoặc Mô hình hóa) để tinh chỉnh. Ghi chép tài liệu đánh giá cẩn thiện.

### 2. Các câu hỏi cần trả lời trước khi bước vào bước tiếp theo

1. Kết quả từ mô hình và các phát hiện (findings) có thực sự giải quyết được triệt để bài toán kinh doanh ban đầu không?
2. Có bất kỳ yếu tố kinh doanh cốt lõi nào bị bỏ sót hoặc chưa được kiểm nghiệm trong mô hình không?
3. Quy trình thực hiện dự án có đảm bảo tính đúng đắn, sạch sẽ và không vi phạm các giả định dữ liệu hay ràng buộc pháp lý nào không?
4. Đâu là quyết định tối ưu lúc này: Tiến hành triển khai ngay hay quay lại vòng lặp để nâng cao chất lượng mô hình?

---

## GIAI ĐOẠN 6: TRIỂN KHAI (DEPLOYMENT)

Việc tạo ra mô hình không phải là điểm kết thúc. Mục đích của dự án là chuyển hóa các tri thức thu được thành hành động thực tế nhằm cải tiến vận hành của tổ chức.

### 1. Các công việc cần làm (Tasks)

* **Lập kế hoạch triển khai (Plan for Deployment):** Tổng hợp các mô hình và phát hiện. Thiết lập một kế hoạch từng bước cụ thể để tích hợp mô hình vào hệ thống thông tin của doanh nghiệp (nêu rõ các chi tiết kỹ thuật, yêu cầu về cơ sở dữ liệu).
* **Lập kế hoạch giám sát và bảo trì (Plan Monitoring and Maintenance):** Thiết kế quy trình theo dõi chất lượng mô hình khi chạy thực tế (giám sát các biến động thị trường, sự thay đổi hành vi theo mùa) nhằm phát hiện thời điểm mô hình bị suy giảm độ chính xác để kích hoạt việc tinh chỉnh hoặc huấn luyện lại mô hình.
* **Tạo báo cáo tổng kết (Produce a Final Report):** Thu thập toàn bộ tài liệu từ các giai đoạn trước để cấu trúc thành một báo cáo tổng thể, chuẩn bị bài thuyết trình (presentation) cho các bên liên quan và ban giám đốc.
* **Đánh giá dự án cuối cùng (Conduct a Final Project Review):** Tổ chức họp tổng kết dự án để ghi nhận những kinh nghiệm thực tế, đánh giá hiệu quả phối hợp và lưu trữ các bài học phục vụ cho tương lai.

### 2. Các điều cần đảm bảo để đóng dự án thành công

1. Bản kế hoạch triển khai đã chỉ rõ thông tin phù hợp sẽ đến đúng người có thẩm quyền xử lý chưa (ví dụ: Nhà quản lý nhận giải thích chiến lược, Lập trình viên Web nhận yêu cầu tích hợp giao diện, Chuyên gia DB nhận cấu trúc thuộc tính mới)?
2. Kế hoạch ứng phó sự cố (Contingency plan) khi quá trình triển khai thực tế gặp lỗi hệ thống hoặc khi các nhà quản lý yêu cầu giải trình sâu hơn về mặt kỹ thuật đã chuẩn bị sẵn sàng chưa?
3. Tiêu chí đánh giá sự lỗi thời của mô hình (Khi nào mô hình không còn áp dụng được nữa) đã được thống nhất cụ thể bằng các con số định lượng chưa?
4. Toàn bộ mã nguồn, tài liệu các bước, và báo cáo cuối cùng đã được đóng gói và lưu trữ đúng quy định chưa?
