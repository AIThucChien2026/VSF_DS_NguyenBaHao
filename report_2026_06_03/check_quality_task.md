# Check Quality Task Plan

Muc tieu cua tai lieu nay la tao mot luong lam viec ro rang cho giai doan dau cua du an Data Science: **Data Understanding -> Check Quality -> EDA**.

Tai lieu nay **khong viet code**. No chi mo ta viec can lam, ly do can lam, ket qua mong doi va diem dung de tranh bi lac huong hoac lam qua nhieu viec thua.

---

## 0. Nguyen tac lam viec

### 0.1. Chi kiem tra nhung gi giup hieu du lieu va giam rui ro sai logic

**Can lam gi?**

- Tap trung vao cau truc bang, grain, khoa, cot quan trong, target neu co, va cac loi du lieu co the lam sai phan tich hoac model.
- Khong mo rong sang feature engineering, modeling, tuning model, hoac bao cao ket qua cuoi.

**Vi sao can lam?**

Giai doan nay chua nham toi viec tao model tot ngay. Muc tieu la dam bao minh hieu du lieu va khong dua du lieu loi vao cac buoc sau.

**Diem dung**

Dung lai khi da tra loi duoc:

- Co bao nhieu bang?
- Moi bang co grain gi?
- Cac khoa chinh, khoa ngoai kha nang la gi?
- Bang nao lien quan truc tiep den bai toan?
- Cac rui ro chat luong du lieu lon nhat la gi?

---

# 1. Data Understanding

## 1.1. Lap danh sach tat ca bang du lieu

**Can lam gi?**

- Liet ke toan bo bang/file du lieu dang co.
- Ghi lai ten bang, so dong, so cot, va vai tro du kien cua tung bang.
- Phan nhom bang theo nghiep vu neu co, vi du: customer, order, product, transaction, return, campaign, rating.

**Muc nay giup ich gi?**

Voi du an nhieu bang, neu khong co ban do tong quan, minh rat de join sai bang, bo sot bang quan trong, hoac phan tich mot bang khong dai dien cho bai toan.

**Can tranh**

- Khong di sau vao tung cot ngay lap tuc.
- Khong ket luan bang nao "vo dung" khi chua hieu quan he voi cac bang khac.

**Ket qua mong doi**

Mot bang tom tat metadata gom:

- Ten bang
- So dong
- So cot
- Vai tro du kien
- Muc do lien quan den bai toan
- Ghi chu nghi van ban dau

## 1.2. Xac dinh grain cua tung bang

**Can lam gi?**

Voi moi bang, tra loi cau hoi: **1 dong trong bang nay dai dien cho cai gi?**

Vi du:

- 1 dong = 1 customer
- 1 dong = 1 order
- 1 dong = 1 order item
- 1 dong = 1 transaction
- 1 dong = 1 return event
- 1 dong = 1 product

**Muc nay giup ich gi?**

Grain la nen tang cua du an nhieu bang. Neu nham grain, cac chi so nhu doanh thu, so don hang, return rate, average rating, conversion rate hoac target ML co the bi tinh sai.

**Can tranh**

- Khong chi nhin ten bang de doan grain.
- Khong join bang khi chua biet join do co lam tang so dong hay khong.

**Ket qua mong doi**

Moi bang co mot mo ta grain ngan gon va ro rang.

## 1.3. Xac dinh khoa chinh va khoa lien ket tiem nang

**Can lam gi?**

- Tim cac cot co kha nang la primary key.
- Tim cac cot co kha nang la foreign key de noi voi bang khac.
- Ghi lai quan he du kien giua cac bang: one-to-one, one-to-many, many-to-one, hay many-to-many.

**Muc nay giup ich gi?**

Day la buoc chong join sai. Mot phep join sai co the lam nhan dong, lam phong dai doanh thu, lam sai ti le, hoac tao leakage cho model.

**Can tranh**

- Khong mac dinh cot ten giong nhau la join duoc.
- Khong mac dinh ID la unique neu chua kiem tra.
- Khong join many-to-many neu chua co ly do nghiep vu ro rang.

**Ket qua mong doi**

Mot so do quan he bang o muc don gian:

- Bang A noi voi Bang B qua khoa nao
- Quan he du kien la gi
- Rui ro join can kiem tra la gi

## 1.4. Hieu y nghia cac cot quan trong

**Can lam gi?**

- Xac dinh cac cot ve ID, thoi gian, so tien, trang thai, nhom san pham, khach hang, target, va cac cot co kha nang dung cho phan tich.
- Ghi lai nhung cot chua ro y nghia.

**Muc nay giup ich gi?**

Cot co ten de hieu sai rat nguy hiem. Vi du `created_at`, `paid_at`, `delivered_at` deu la thoi gian nhung phuc vu cac cau hoi khac nhau. Neu dung sai cot thoi gian, phan tich xu huong va train/test split co the sai.

**Can tranh**

- Khong doi ten cot hoac loai cot o buoc nay neu chua co ly do.
- Khong gan nghia nghiep vu cho cot khi chi moi doan.

**Ket qua mong doi**

Danh sach cot quan trong, y nghia du kien, va cau hoi can xac minh.

## 1.5. Xac dinh muc tieu phan tich hoac target ML neu da co

**Can lam gi?**

- Neu du an co target, ghi ro target la cot nao, nam o bang nao, va grain cua target la gi.
- Neu chua co target, ghi ro cac cau hoi phan tich tam thoi.

**Muc nay giup ich gi?**

Tat ca buoc check quality va EDA nen phuc vu muc tieu cuoi. Neu khong co target hoac cau hoi phan tich, minh de bi sa vao ve bieu do hoac thong ke khong can thiet.

**Can tranh**

- Khong tao target moi khi chua hieu nghiep vu.
- Khong dua cot sau thoi diem target vao phan tich ML vi co nguy co leakage.

**Ket qua mong doi**

Mot mo ta ngan gon:

- Target/cau hoi chinh la gi
- Don vi du doan/phan tich la gi
- Thoi diem nao duoc xem la moc quan sat

---

# 2. Check Quality

## 2.1. Kiem tra schema va kieu du lieu

**Can lam gi?**

- Kiem tra kieu du lieu cua tung cot.
- Danh dau cot dang sai kieu, vi du ngay thang dang la text, so tien dang la text, ID bi doc thanh so.

**Muc nay giup ich gi?**

Sai kieu du lieu lam sai thong ke, sai sort theo thoi gian, sai groupby, va co the lam model hieu nham bien categorical thanh numeric.

**Can tranh**

- Khong sua toan bo kieu du lieu mot cach tu dong.
- Khong ep kieu neu chua biet format va gia tri bat thuong.

**Ket qua mong doi**

Danh sach cot can xem lai kieu du lieu va muc do anh huong.

## 2.2. Kiem tra missing values

**Can lam gi?**

- Kiem tra ty le missing theo cot va theo bang.
- Phan biet missing that su, missing do khong ap dung, va missing co y nghia nghiep vu.

**Muc nay giup ich gi?**

Missing khong phai luc nao cung la loi. Trong du an that, missing co the cho biet trang thai don hang, kenh ban, hanh vi khach hang, hoac loi thu thap du lieu.

**Can tranh**

- Khong xoa dong/cot chi vi co null.
- Khong fill missing bang gia tri trung binh/mode khi chua biet ly do missing.

**Ket qua mong doi**

Bang tong hop missing:

- Cot nao missing nhieu
- Missing co tap trung o nhom nao khong
- Missing anh huong den join, target, hoac metric nao

## 2.3. Kiem tra duplicate va unique key

**Can lam gi?**

- Kiem tra cot du kien la primary key co unique khong.
- Kiem tra duplicate dong hoac duplicate theo nhom khoa nghiep vu.

**Muc nay giup ich gi?**

Duplicate co the lam nhan doanh thu, dem sai so luong don hang, hoac lam train/test bi trung mau. Voi du lieu nhieu bang, duplicate key con lam join nhan dong.

**Can tranh**

- Khong xoa duplicate ngay khi thay trung.
- Can phan biet duplicate loi voi duplicate hop le do grain chi tiet hon minh tuong.

**Ket qua mong doi**

Danh sach bang/cot co duplicate dang nghi va anh huong tiem nang.

## 2.4. Kiem tra tinh hop le cua gia tri

**Can lam gi?**

Kiem tra cac gia tri vo ly theo nghiep vu:

- So tien am bat thuong
- So luong bang 0 hoac am
- Ngay ket thuc truoc ngay bat dau
- Rating ngoai thang diem
- Trang thai khong nam trong nhom hop le
- Tuoi, khoang cach, discount, tax, profit co gia tri bat thuong

**Muc nay giup ich gi?**

Gia tri vo ly co the lam metric va model lech manh. Dac biet voi cot tien, so luong, thoi gian va target, loi nho co the tao ket luan sai.

**Can tranh**

- Khong coi moi outlier la loi.
- Khong sua gia tri bat thuong khi chua co bang chung nghiep vu.

**Ket qua mong doi**

Danh sach rule kiem tra hop le va cac cot vi pham rule.

## 2.5. Kiem tra logic thoi gian

**Can lam gi?**

- Kiem tra thu tu cac moc thoi gian trong cung mot ban ghi.
- Kiem tra phan bo du lieu theo ngay/thang/nam.
- Xac dinh co giai doan nao du lieu bi mat, bi dut, hoac tang giam bat thuong.

**Muc nay giup ich gi?**

Thoi gian anh huong truc tiep den EDA, split train/test, leakage, va cach dien giai xu huong. Neu moc thoi gian sai, cac phan tich sau rat de sai.

**Can tranh**

- Khong tron du lieu tuong lai vao du lieu qua khu khi chuan bi ML.
- Khong dung random split neu bai toan co tinh thoi gian ma chua danh gia rui ro.

**Ket qua mong doi**

Ket luan ve do tin cay cua cac cot thoi gian va khoang thoi gian du lieu bao phu.

## 2.6. Kiem tra rui ro join giua cac bang

**Can lam gi?**

- Voi moi cap bang can join, kiem tra duplicate key o hai phia.
- Du kien so dong truoc va sau join.
- Ghi ro join giu grain nao va co lam thay doi grain khong.

**Muc nay giup ich gi?**

Trong du an nhieu bang, join la diem de sai logic nhat. Join sai co the tao many-to-many ngoai y muon, lam nhan dong va sai toan bo metric.

**Can tranh**

- Khong join tat ca bang thanh mot bang lon khi chua co muc tieu ro.
- Khong aggregate sau join de "sua" so dong neu chua hieu vi sao so dong tang.

**Ket qua mong doi**

Mot bang danh gia join:

- Bang trai
- Bang phai
- Khoa join
- Quan he du kien
- Rui ro nhan dong
- Grain sau join

## 2.7. Kiem tra rui ro target leakage neu co ML

**Can lam gi?**

- Danh dau cac cot xuat hien sau thoi diem target.
- Danh dau cac cot co the la ban sao hoac bien doi truc tiep cua target.
- Danh dau cac cot chi ton tai sau khi ket qua da xay ra.

**Muc nay giup ich gi?**

Leakage lam model co diem so dep gia nhung that bai khi dung that. Trong du an that, day la mot trong nhung rui ro nghiem trong nhat.

**Can tranh**

- Khong dua tat ca cot co predictive power cao vao model neu chua kiem tra thoi diem phat sinh.
- Khong danh gia model truoc khi loai tru rui ro leakage lon.

**Ket qua mong doi**

Danh sach cot can cam, can canh bao, hoac can xac minh truoc khi modelling.

---

# 3. EDA

## 3.1. EDA tong quan theo tung bang

**Can lam gi?**

- Xem phan bo cac cot numeric quan trong.
- Xem tan suat cac cot categorical quan trong.
- Xem khoang thoi gian va muc do day du cua tung bang.

**Muc nay giup ich gi?**

EDA tung bang giup hieu hanh vi rieng cua du lieu truoc khi join. Neu join qua som, minh co the khong biet loi den tu bang nao.

**Can tranh**

- Khong ve qua nhieu bieu do cho moi cot.
- Chi uu tien cot lien quan den grain, target, metric, hoac join.

**Ket qua mong doi**

Nhan xet ngan gon cho tung bang:

- Bang nay noi gi ve nghiep vu?
- Cot nao dang bat thuong?
- Bang nay co dang tin de dung tiep khong?

## 3.2. EDA theo target hoac cau hoi chinh

**Can lam gi?**

- Neu co target, xem phan bo target va moi quan he ban dau voi cac nhom quan trong.
- Neu chua co target, chon mot so metric chinh de quan sat, vi du doanh thu, so don, return rate, rating, churn, conversion.

**Muc nay giup ich gi?**

Buoc nay gan EDA voi muc tieu du an. No giup tranh viec ve nhieu bieu do dep nhung khong tra loi cau hoi nao.

**Can tranh**

- Khong ket luan nhan qua chi tu EDA.
- Khong chon feature chi vi thay bieu do co ve lien quan, neu chua kiem tra leakage va grain.

**Ket qua mong doi**

Mot danh sach insight ban dau va cac cau hoi can kiem tra tiep.

## 3.3. EDA theo thoi gian

**Can lam gi?**

- Xem metric chinh thay doi theo ngay, thang, quy hoac giai doan phu hop.
- Kiem tra seasonality, trend, su kien tang giam bat thuong, va khoang thoi gian thieu du lieu.

**Muc nay giup ich gi?**

Nhieu bai toan Data Science bi anh huong boi thoi gian. Neu du lieu thay doi theo mua vu hoac giai doan, cach split va cach danh gia model cung phai can nhac lai.

**Can tranh**

- Khong lam qua nhieu time series neu bai toan khong can.
- Khong binh luan xu huong khi du lieu qua it hoac bi dut doan.

**Ket qua mong doi**

Ket luan so bo ve tinh on dinh cua du lieu theo thoi gian.

## 3.4. EDA theo nhom nghiep vu

**Can lam gi?**

- So sanh metric chinh theo cac nhom nhu product category, customer segment, region, channel, status, campaign.
- Kiem tra nhom nao co volume qua nho de ket luan.

**Muc nay giup ich gi?**

Phan tich theo nhom giup tim pattern co y nghia kinh doanh. Dong thoi, no giup phat hien nhom du lieu bi loi, thieu, hoac co hanh vi khac thuong.

**Can tranh**

- Khong dua ra ket luan manh tu nhom co so mau nho.
- Khong so sanh cac nhom khi grain hoac cach tinh metric khong dong nhat.

**Ket qua mong doi**

Danh sach nhom co pattern dang chu y va nhom can canh bao do sample size nho.

## 3.5. EDA sau join neu that su can

**Can lam gi?**

- Chi join cac bang can thiet de tra loi cau hoi ro rang.
- Sau join, kiem tra lai so dong, grain, duplicate key, missing moi phat sinh, va metric co bi thay doi bat thuong khong.

**Muc nay giup ich gi?**

EDA sau join cho phep phan tich moi quan he giua cac thuc the, vi du customer voi order, product voi return, campaign voi transaction. Nhung no chi an toan khi join duoc kiem soat.

**Can tranh**

- Khong bien EDA thanh viec tao mot "mega table" gom tat ca moi thu.
- Khong tin vao insight sau join neu chua validate grain va so dong.

**Ket qua mong doi**

Mot so insight lien bang co kiem soat, kem ghi chu ro rang ve join da dung.

---

# 4. Output cuoi cua giai doan nay

## 4.1. Data understanding summary

Can co:

- Danh sach bang
- Grain tung bang
- Khoa chinh/khoa ngoai du kien
- Vai tro tung bang trong bai toan
- Cac cot quan trong va cot chua ro nghia

## 4.2. Data quality report

Can co:

- Missing values dang chu y
- Duplicate/key issue
- Sai kieu du lieu
- Gia tri bat hop ly
- Loi logic thoi gian
- Rui ro join
- Rui ro target leakage neu co

## 4.3. EDA summary

Can co:

- Insight ban dau co lien quan den muc tieu
- Pattern theo thoi gian neu co
- Pattern theo nhom nghiep vu
- Bat thuong can dieu tra tiep
- Nhung dieu chua du bang chung de ket luan

---

# 5. Nhung viec chua nen lam o giai doan nay

## 5.1. Chua nen clean data manh tay

Khong nen xoa null, xoa outlier, sua duplicate, hoac ep kieu hang loat khi chua co ly do va bang chung. Giai doan nay uu tien phat hien va ghi nhan rui ro.

## 5.2. Chua nen feature engineering

Chua nen tao nhieu feature moi khi chua hieu grain, target va leakage. Feature tao som co the dep ve mat ky thuat nhung sai ve logic du lieu.

## 5.3. Chua nen train model

Model chi nen lam sau khi da biet du lieu co dang tin khong, target co ro khong, split co hop ly khong, va feature co leak khong.

## 5.4. Chua nen ve qua nhieu bieu do

EDA khong phai la ve cang nhieu cang tot. Moi bieu do nen tra loi mot cau hoi cu the hoac kiem tra mot rui ro cu the.

---

# 6. Thu tu uu tien thuc hien

## Uu tien 1: Hieu cau truc du lieu

Lam truoc:

- Liet ke bang
- Xac dinh grain
- Xac dinh khoa
- Xac dinh target/cau hoi chinh

## Uu tien 2: Kiem tra rui ro lam sai ket qua

Lam tiep:

- Duplicate key
- Missing quan trong
- Kieu du lieu sai
- Gia tri vo ly
- Logic thoi gian
- Rui ro join
- Leakage neu co ML

## Uu tien 3: EDA co muc dich

Lam sau:

- EDA tung bang
- EDA theo target/metric chinh
- EDA theo thoi gian
- EDA theo nhom nghiep vu
- EDA sau join khi can

---

# 7. Tieu chi hoan thanh

Giai doan Data Understanding -> Check Quality -> EDA duoc xem la tam on khi:

- Biet moi bang co grain gi.
- Biet bang nao can cho bai toan, bang nao chi phu tro.
- Biet join nao an toan, join nao co rui ro.
- Biet cac loi du lieu lon nhat va anh huong cua chung.
- Biet target hoac metric chinh co dang tin de phan tich tiep khong.
- Co insight EDA ban dau nhung khong ket luan qua muc.
- Co danh sach cau hoi can xac minh truoc khi cleaning, feature engineering va modeling.
