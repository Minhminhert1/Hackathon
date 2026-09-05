# FXVN Parser — Bóc tách giao dịch USD/VND từ chat dealing

## Mục đích
Đọc tin nhắn thô (jsonl) từ phòng chat FXVN, tự động nhận diện quote và ghép thành giao dịch (deal) có cấu trúc: ai bán, ai mua, giá, khối lượng.

## Cấu trúc
- `bank_resolver.py` — chuẩn hóa & nhận diện ngân hàng (tên đầy đủ, tên thường, mã SWIFT, mã giao dịch riêng)
- `bank_mapping.json` — bảng 33 ngân hàng + alias. SỬA FILE NÀY khi gặp mã bank mới.
- `classify.py` — phân loại mỗi tin: quote_spot / quote_swap / confirm / noise
- `deal_matcher.py` — ghép deal theo luật nghiệp vụ
- `run_parser.py` — chạy toàn bộ, xuất quotes.json + deals.json

## Chạy
```
python run_parser.py data-2026-09-05.jsonl
```

## LUẬT GHÉP DEAL (đã chốt với dealer)
- A = người quote (offer/bid + giá [+ tenor])
- B = người nhảy vào ĐÚNG CHIỀU NGƯỢC (A offer → B bid). A offer=A bán=seller.
- Deal chốt khi A nói "done" + tên/bank đối tác. Người done phải là A.
- GIÁ = con số cuối cùng hai bên đồng ý trước done (B có thể counter, A đồng ý thì lấy giá B).
- VOLUME = số ở tin done; thiếu thì suy từ B (hạ confidence).
- Một done nhiều tên → tách nhiều deal.
- Áp dụng chung spot & swap; deal gắn kind=spot/swap. Spot: giá 2 số → 26.2xx.

## CÒN CẦN HOÀN THIỆN (20% khó)
1. Ghép B theo tên gọi thân mật (first name VN) — nhiều deal đang ?→? do tên gọi != tên đầy đủ.
2. Dựng giá big-figure TRƯỢT (hiện hardcode 26.2xx) — khi giá qua mốc trăm sẽ sai.
3. Kiểm tra biên NHNN cho giá dựng ra; ngoài biên → review.
4. Vòng đời quote (valid/pulled/hit) để dựng best bid/offer theo thời gian.
5. LLM tầng 2 cho các câu tự nhiên classify không bắt được (type='other','partial').
6. Tách swap sang pipeline riêng khi cần mở rộng.

## ĐO CHẤT LƯỢNG
Chạy parser → so deals.json với golden set (label tay). Đo precision/recall riêng cho deal, và sai số giá/volume.
