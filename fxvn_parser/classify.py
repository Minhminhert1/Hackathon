"""
classify.py — Phân loại mỗi tin nhắn và trích xuất thông tin quote spot.
Loại: quote_spot / quote_swap / confirm / noise
"""
import re

# --- Từ điển ---
TENOR = re.compile(r'\b(o/?n|tn|s/?n|spot ?next|tod|tom|tomorrow|\d+ ?[wmy]|1w|2w|3w|1m|2m|3m|6m|9m|1y|đóng ngày|dong ngay|eod|\d+ds|ds)\b', re.I)
SIDE_BID = re.compile(r'\b(bid|mua|buy)\b', re.I)
SIDE_OFF = re.compile(r'\b(offer|off|ask|sell|bán|ban|có|con)\b', re.I)
CONFIRM = re.compile(r'\b(done|khớp|khop|nhận|nhan)\b', re.I)
# volume: số kèm u/mio/tr/k
VOL = re.compile(r'(\d+(?:\.\d+)?)\s*(u|mio|tr|k)\b', re.I)
VOL_EACH = re.compile(r'(\d+(?:\.\d+)?)\s*(?:u\s*)?each', re.I)
# giá spot: số 2 chữ số vùng 40-99 (26.240-26.299)
SPOT_PRICE = re.compile(r'(?<![\d.])([4-9]\d)(?![\d.])')
# giá swap: số thập phân phần nguyên nhỏ, hoặc số âm
SWAP_NUM = re.compile(r'(?<!\d)(-?\d\.\d+)')
# noise thuần
NOISE = re.compile(r'^(hi|hello|morning|good\s|nice|thank|thanks|thx|tks|ok|oki|okie|a tks|e tks|em tks|a thank|cảm ơn|cam on|gm|good morning|morning all|nice friday|thanks all|only|pls|please)[\s\.,!]*$', re.I)
PM = re.compile(r'\b(pm|dm)\b.*\bpls\b|\bpm pls\b', re.I)

def is_emoji_only(t):
    return len(t.strip()) <= 3 and not re.search(r'[a-z0-9]', t, re.I)

def classify(text: str) -> dict:
    """Trả về loại + thông tin trích được. Không quyết định deal ở đây (deal cần ngữ cảnh)."""
    t = text.strip()
    has_tenor = bool(TENOR.search(t))
    has_confirm = bool(CONFIRM.search(t))
    side = None
    if SIDE_OFF.search(t): side = 'offer'
    if SIDE_BID.search(t): side = 'bid' if side is None else 'two_way'

    # volume
    vol = None
    m = VOL.search(t) or VOL_EACH.search(t)
    if m: vol = float(m.group(1))

    # giá — loại bỏ cụm volume (50u, 3mio, 500k) trước khi bắt giá spot
    t_noVol = re.sub(r'\d+(?:\.\d+)?\s*(?:u|mio|tr|k|each)\b', ' ', t, flags=re.I)
    spot_prices = [int(x) for x in SPOT_PRICE.findall(t_noVol)]
    swap_nums = [float(x) for x in SWAP_NUM.findall(t)]

    # --- phân loại ---
    if is_emoji_only(t) or NOISE.match(t) or PM.search(t):
        # nhưng nếu có confirm + tên/vol thì vẫn là confirm (vd "done a, e tks" đã bị NOISE bắt hụt)
        if not has_confirm:
            return {'type': 'noise'}

    if has_confirm:
        typ = 'confirm'
        kind = 'swap' if has_tenor else 'spot'
        return {'type': typ, 'kind': kind, 'side': side, 'volume': vol,
                'spot_prices': spot_prices, 'swap_nums': swap_nums, 'has_tenor': has_tenor}

    if has_tenor or (swap_nums and not spot_prices):
        return {'type': 'quote_swap', 'side': side, 'volume': vol, 'swap_nums': swap_nums}

    if side and spot_prices:
        # quote spot: có side + giá 2 số
        if len(spot_prices) >= 2 and side != 'two_way':
            side = 'two_way'
        return {'type': 'quote_spot', 'side': side, 'volume': vol, 'spot_prices': spot_prices}

    if spot_prices and not side:
        # chỉ có số, không side -> có thể là giá hai chiều "80 85" hoặc nối tiếp tin trước
        if len(spot_prices) >= 2:
            return {'type': 'quote_spot', 'side': 'two_way', 'volume': vol, 'spot_prices': spot_prices}
        return {'type': 'partial', 'spot_prices': spot_prices, 'volume': vol}

    return {'type': 'other'}
