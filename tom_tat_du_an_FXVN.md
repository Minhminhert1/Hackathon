# Tóm tắt dự án — MSB AI Hackathon 2026: Công cụ phân tích thị trường FX từ chat dealing

## 1. Bối cảnh & ý tưởng

Dự thi **MSB AI Hackathon 2026** (chủ đề "AI Agents for MSB", làm trong 1 tháng), thuộc khối **Treasury / Khách hàng Doanh nghiệp**.

**Ý tưởng chốt:** Ứng dụng AI vào trading UV (USD/VND). Lấy dữ liệu từ phòng chat dealing liên ngân hàng trên **LSEG Workspace Messenger** (phòng "FXVN", ~251 thành viên), bóc tách thành giao dịch có cấu trúc, rồi phân tích xu hướng mua/bán của thị trường.

**Định vị sản phẩm:** công cụ **quan sát & phân tích thị trường** — đọc thông tin cung/cầu từ chat để hiểu thị trường, KHÔNG phải công cụ tự động đặt lệnh. Framing này khớp điều khoản LSEG (phòng chat không phải nơi thực hiện giao dịch) và tránh rủi ro giao dịch tự động.

## 2. Lưu ý tuân thủ (cần xử lý trước production)

- **Trích xuất chat LSEG:** cần Pháp chế MSB rà soát hợp đồng license với LSEG về quyền trích xuất tự động. Với hackathon: dùng dữ liệu ẩn danh, nói rõ nguồn.
- **Dữ liệu nhạy cảm:** chat dealing có danh tính đối tác, giá, khối lượng. Không lưu lên cloud cá nhân; ưu tiên hạ tầng trong nước / tài khoản công ty.
- **Con đường bền vững:** LSEG có feed chính thức **UMF (User Message Feed)** chạy headless, hợp lệ — nên định vị là hướng production, dù hackathon chưa dùng.

## 3. Hành trình kỹ thuật — cách lấy dữ liệu

Quá trình trinh sát (dò cách lấy dữ liệu) đã loại trừ dần các phương án:

| Phương án | Kết quả |
|---|---|
| API chính thức | Có (UMF) nhưng cần license trả phí, không kịp cho hackathon |
| Chặn WebSocket | ❌ Chết — nội dung bị **mã hóa đầu-cuối (E2EE)**, frame chỉ chứa ciphertext |
| **Scrape DOM** | ✅ Đường khả thi — text đã giải mã nằm trong DOM sau khi app render |

**Phát hiện quan trọng:** LSEG Messenger mã hóa E2EE ở tầng truyền tin (dùng Ably WebSocket, JSON), nên chỉ đọc được nội dung ở tầng DOM (giao diện). Đây cũng là lý do phải dùng DOM scraping thay vì bắt gói mạng.

### Cấu trúc DOM đã xác định
Mỗi tin nhắn nằm trong thẻ `div.incoming-message` với đầy đủ thuộc tính:
- `data-message-id` — mã duy nhất (chống trùng)
- `data-sender-name` — tên người gửi
- `data-company` — tên ngân hàng đầy đủ
- `data-timestamp` — giờ (hh:mm:ss)
- `data-date` — ngày
- Nội dung: thẻ con `[data-testid="parsed-raw-message"]`
- Container gốc: `#conversation-container`

## 4. Công cụ thu thập (đã hoạt động)

Kiến trúc tách 2 phần:
- **Extension Chrome:** dùng MutationObserver gắn vào `#conversation-container`, bắt tin ngay khi xuất hiện (vì trang dùng **virtual scrolling** — tin cũ bị xóa khỏi DOM khi cuộn qua), chống trùng theo `message_id`, gán số thứ tự `seq`, gửi về server local.
- **Server Python (FastAPI):** nhận và ghi ra file `.jsonl` theo ngày.

Máy dùng: Windows, Python 3.13.3, Chrome bật được Developer mode. Được dựng bằng Antigravity.

### Vấn đề đã phát hiện & xử lý
- **Thứ tự tin bị xáo trộn** (413/1077 lần đảo): `seq` gán theo thứ tự cuộn màn hình, không theo thời gian. **Cách sửa:** sắp lại theo `timestamp`, cùng giây thì theo `seq`.
- Cần bổ sung: heartbeat (cảnh báo khi ngừng bắt), bắt cả tin gửi đi (outgoing), xử lý đa phòng.

## 5. Luật nghiệp vụ — bóc tách giao dịch

### Phân loại tin nhắn (4 loại)
- **Quote** (chào giá): có side (bid/offer) + giá
- **Deal** (giao dịch đã khớp): tin "done" + đối tác
- **Swap/Forward:** có kỳ hạn (ON, tom, 1w, 1m...) — điểm swap là số thập phân nhỏ (2.3, 1.5). Giai đoạn này **gắn nhãn để loại trừ**, tập trung spot trước.
- **Noise:** chào hỏi, cảm ơn, emoji, "pm pls"

### Luật ghép deal (đã chốt với dealer)
- **A = người quote** (mở giá). **B = người nhảy vào**, đúng chiều ngược lại (A offer → B bid).
- Deal chốt khi **A nói "done" + tên/bank đối tác**. Người done phải là người quote gốc A.
- **Giá khớp = con số cuối cùng hai bên cùng đồng ý trước "done"** (nếu B trả giá khác và A đồng ý thì lấy giá B, không phải giá A ban đầu).
- **Volume = số ở tin done** (đơn vị u = triệu USD). Thiếu thì suy từ B, hạ độ tin cậy.
- **Một "done" nhiều tên → tách nhiều deal.**
- B nhảy vào cũng tự thành quote mới (người thứ 3 có thể nhảy vào B).
- Luật áp dụng chung cho spot & swap; chỉ khác cách đọc giá.

### Dựng giá đầy đủ
Dealer chỉ gõ 2 số cuối. Giá USD/VND spot vùng **26.2xx** → "83" = 26.283.
Lưu ý: cần logic "big figure trượt" khi giá qua mốc trăm (chưa hardcode), và kiểm tra biên NHNN.

## 6. Parser (đã viết & chạy thật)

Bộ parser Python 5 file, chạy trên 1077 tin thật ngày 4/9:
- `bank_resolver.py` — chuẩn hóa & nhận diện ngân hàng (tên đầy đủ, tên thường, mã SWIFT, **mã giao dịch riêng** như ICB, PGBV, VNTT, KLBV...)
- `bank_mapping.json` — 33 ngân hàng + alias
- `classify.py` — phân loại tin
- `deal_matcher.py` — ghép deal theo luật trên
- `run_parser.py` — chạy toàn bộ

**Kết quả:** 271 quote spot, 146 deal spot (18 chắc chắn cao, 101 trung bình, 27 cần review).

### Còn cần hoàn thiện (20% khó)
1. Ghép đối tác theo tên gọi thân mật tiếng Việt (nhiều deal còn `?→?`)
2. Big-figure trượt thay vì hardcode 26.2xx
3. Kiểm tra biên NHNN
4. Vòng đời quote (live/pulled/hit) để dựng best bid/offer theo thời gian
5. LLM tầng 2 cho câu tự nhiên grammar không bắt được
6. Tách pipeline swap khi mở rộng

## 7. Golden set (để đo chất lượng)

Cần **label tay** một phiên đầy đủ làm "đáp án" để chấm điểm parser (precision/recall tách bạch cho deal, sai số giá/volume). Lưu ý: label phải gắn `message_id` thật (không dùng mã tự chế từ PDF) thì mới nối được với output parser. Việc này giao AI khác làm song song, dùng file đã sắp xếp + bảng bank đầy đủ.

## 8. Dashboard web (đã export)

File `fxvn_dashboard.html` — web tự chứa, mở bằng trình duyệt là chạy:
- **Lọc theo ngân hàng và theo dealer**
- Thẻ số tổng quan (số quote, vùng giá, xu hướng)
- Đường giá thị trường theo giờ
- Xu hướng mua/bán theo bank (net bid−offer)
- Bảng chi tiết theo từng dealer
- Nút nạp file `.jsonl` mới

**Insight từ dữ liệu ngày 4/9:** giá giảm dần suốt phiên (26.289 lúc 9h → 26.256 lúc 16h); VIB & BIDV xả bán mạnh, VietBank & BacABank gom mua mạnh.

## 9. Chiến lược pitch & demo

- **Bộ phát lại (replay):** ghi một phiên sôi động, phát lại tua nhanh khi demo — không phụ thuộc thị trường sống, đồng thời là bộ test parser.
- **Kiến trúc adapter:** tầng thu thập tách riêng → hackathon dùng DOM, production chuyển UMF chỉ bằng đổi cấu hình. Biến điểm yếu (DOM scraping) thành bằng chứng nghĩ xa.
- **Con số thật:** chuẩn bị precision/recall trên golden set — "chạy trên X tin thật, bắt đúng Y% deal".
- **Nhấn E2EE:** phát hiện Messenger mã hóa đầu-cuối cho thấy hiểu hệ thống ở tầng sâu.
- Định vị "quan sát thị trường" (không phải giao dịch tự động) để tránh mọi câu hỏi rủi ro.

## 10. Các bước tiếp theo

1. Gia cố công cụ thu thập: heartbeat, outgoing, đa phòng (giao Claude Code review code Antigravity).
2. Hoàn thiện parser 20% khó (ghép tên, big-figure trượt).
3. AI khác label golden set song song → đo parser.
4. Vòng lặp: đo → sửa → đo lại trên cùng dữ liệu.
5. Mở rộng: best bid/offer theo thời gian, ghép lớp deal thật lên dashboard, tách pipeline swap.

---

*Tài liệu tóm tắt quá trình thảo luận thiết kế & xây dựng. Các file kèm theo: bộ parser (`fxvn_parser.zip`), dashboard (`fxvn_dashboard.html`), bảng bank (`bank_mapping.json`).*
