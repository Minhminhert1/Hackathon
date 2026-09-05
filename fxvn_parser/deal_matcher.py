"""
deal_matcher.py — Ghép giao dịch từ chuỗi tin nhắn đã sắp theo thời gian.

LUẬT (chốt cùng người dùng):
- A = người quote (mở giá: offer/bid + giá [+ tenor])
- B = người nhảy vào ĐÚNG CHIỀU NGƯỢC LẠI (A offer -> B bid/buy), thường gọi tên A
- Deal chốt khi A nói "done" + tên đối tác (hoặc bank code / mã giao dịch)
- Người done PHẢI là người quote gốc A (hoặc là B xác nhận lại — đánh dấu review)
- GIÁ khớp = con số cuối cùng hai bên cùng đồng ý trước done (có thể là giá B counter, không nhất thiết giá A ban đầu)
- VOLUME = số ở tin done; nếu done không có, suy từ B, hạ confidence
- Một done nhiều tên -> tách nhiều deal
- Áp dụng chung spot & swap; deal gắn nhãn kind=spot/swap
"""
import re
from classify import classify, CONFIRM
from bank_resolver import norm

# tên gọi trong done: lấy các "từ" có thể là tên người (viết hoa đầu) hoặc bank code
NAME_TOKEN = re.compile(r'\b([A-ZÀ-Ỹ][a-zà-ỹ]+|[A-Z]{2,5})\b')

def first_name(full_name: str) -> str:
    """Tên gọi thân mật thường là từ CUỐI trong tên VN (Nguyen Van Minh -> Minh)."""
    parts = full_name.strip().split()
    return parts[-1] if parts else full_name

def match_deals(msgs, resolver, window_before=40):
    """
    msgs: list dict đã sắp thời gian, mỗi dict có order, sender_name, bank_code, text
    Trả về danh sách deal.
    """
    deals = []
    # tiền xử lý: gán classify cho từng tin
    for m in msgs:
        m['_cls'] = classify(m['text'])
        m['_first'] = first_name(m['sender_name'])

    for i, m in enumerate(msgs):
        cls = m['_cls']
        if cls['type'] != 'confirm':
            continue
        confirmer = m           # người nói done (kỳ vọng = A, người quote gốc)
        text = m['text']

        # tìm các tên/bank được nhắc trong tin done
        mentioned_banks = resolver.find_in_text(text)
        # tên người được nhắc (loại bỏ chính từ 'done','tks'...)
        raw_names = [w for w in NAME_TOKEN.findall(text)
                     if norm(w) not in ('done','tks','thanks','thank','nhe','nhé','only','a','e','em','c','anh','chi','test','sr')]

        # volume ở tin done
        done_vol = cls.get('volume')
        # each -> nhiều deal cùng volume
        is_each = bool(re.search(r'each', text, re.I))

        # nhìn ngược để tìm quote gốc của confirmer (A quote) và (các) B đối ứng
        lo = max(0, i - window_before)
        context = msgs[lo:i]

        # quote gần nhất của chính confirmer trước đó = quote gốc A
        a_quote = None
        for c in reversed(context):
            if c['sender_name'] == confirmer['sender_name'] and c['_cls']['type'] in ('quote_spot','quote_swap'):
                a_quote = c; break

        # ứng viên B: những người nhảy vào đúng chiều ngược, trong context
        # xác định chiều A
        a_side = a_quote['_cls'].get('side') if a_quote else None
        want_b_side = None
        if a_side == 'offer': want_b_side = 'bid'
        elif a_side == 'bid': want_b_side = 'offer'

        # tạo deal theo từng đối tác được nhắc trong done
        targets = []
        # ưu tiên bank code nhắc trong done
        for bc in mentioned_banks:
            targets.append(('bank', bc))
        for nm in raw_names:
            # bỏ nếu trùng tên chính người done
            if norm(nm) != norm(confirmer['_first']):
                targets.append(('name', nm))

        # dedup targets giữ thứ tự
        seen_t=set(); targets=[x for x in targets if not (x in seen_t or seen_t.add(x))]
        # nếu đã có bank cụ thể, bỏ các name lẻ trùng người (tránh nhân đôi 'done SHB 20u')
        if any(k=='bank' for k,_ in targets):
            targets=[x for x in targets if x[0]=='bank']
        if not targets:
            targets = [('unknown', None)]

        # dựng deal
        for kind_t, val in targets:
            # tìm B cụ thể trong context khớp target
            b_msg = None
            for c in reversed(context):
                if c['sender_name'] == confirmer['sender_name']:
                    continue
                if kind_t == 'bank' and c.get('bank_code') == val:
                    b_msg = c; break
                if kind_t == 'name' and norm(val) in norm(c['sender_name']):
                    b_msg = c; break

            # giá: ưu tiên giá trong chính tin done, else giá b_msg, else a_quote
            price = None
            kind = 'swap' if m['_cls'].get('has_tenor') else 'spot'
            if kind == 'spot':
                ps = m['_cls'].get('spot_prices') or []
                if ps: price = ps[-1]
                elif b_msg and b_msg['_cls'].get('spot_prices'): price = b_msg['_cls']['spot_prices'][-1]
                elif a_quote and a_quote['_cls'].get('spot_prices'): price = a_quote['_cls']['spot_prices'][-1]
            else:
                sn = m['_cls'].get('swap_nums') or []
                if sn: price = sn[-1]
                elif b_msg and b_msg['_cls'].get('swap_nums'): price = b_msg['_cls']['swap_nums'][-1]
                elif a_quote and a_quote['_cls'].get('swap_nums'): price = a_quote['_cls']['swap_nums'][-1]

            # volume
            vol = done_vol
            if vol is None and b_msg and b_msg['_cls'].get('volume'):
                vol = b_msg['_cls']['volume']

            # xác định buyer/seller theo chiều của A
            buyer_bank = seller_bank = None
            a_bank = confirmer.get('bank_code')
            b_bank = b_msg.get('bank_code') if b_msg else (val if kind_t=='bank' else None)
            if a_side == 'offer':      # A bán -> A seller, B buyer
                seller_bank, buyer_bank = a_bank, b_bank
            elif a_side == 'bid':      # A mua -> A buyer, B seller
                buyer_bank, seller_bank = a_bank, b_bank

            # confidence
            conf = 'high'
            if a_quote is None: conf = 'low'
            elif b_msg is None: conf = 'medium'
            elif price is None or vol is None: conf = 'medium'

            deals.append({
                'confirm_order': m['order'],
                'kind': kind,
                'A_trader': confirmer['sender_name'], 'A_bank': a_bank, 'A_side': a_side,
                'B_target': val, 'B_bank': b_bank,
                'buyer_bank': buyer_bank, 'seller_bank': seller_bank,
                'price_short': price, 'volume': vol,
                'confidence': conf,
                'confirm_text': m['text'],
                'a_quote_order': a_quote['order'] if a_quote else None,
                'b_order': b_msg['order'] if b_msg else None,
            })
    return deals
