"""
bank_resolver.py — Chuẩn hóa tên ngân hàng và nhận diện bank từ text.
Dùng cho parser FXVN. Không phụ thuộc thư viện ngoài.
"""
import json, re, unicodedata, os

def strip_accents(s: str) -> str:
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

def norm(s: str) -> str:
    """Chuẩn hóa: bỏ dấu, thường hóa, gộp khoảng trắng."""
    return re.sub(r'\s+', ' ', strip_accents(s).lower()).strip()

class BankResolver:
    def __init__(self, mapping_path):
        with open(mapping_path, encoding='utf-8') as f:
            data = json.load(f)
        self.banks = data['banks']
        # full name (đã chuẩn hóa) -> code
        self.full2code = {norm(b['full']): b['code'] for b in self.banks}
        # alias (đã chuẩn hóa) -> code ; sắp alias dài trước để ưu tiên khớp cụ thể
        self.alias2code = {}
        for b in self.banks:
            for a in b['aliases']:
                self.alias2code[norm(a)] = b['code']
        # danh sách alias sắp theo độ dài giảm dần để tìm trong text
        self.alias_sorted = sorted(self.alias2code.keys(), key=len, reverse=True)

    def from_company(self, company: str):
        """Lấy code từ tên đầy đủ (data-company)."""
        return self.full2code.get(norm(company))

    def find_in_text(self, text: str):
        """Tìm mọi mã bank được nhắc trong text (dùng cho 'done SHB 20u')."""
        t = norm(text)
        found = []
        for a in self.alias_sorted:
            # khớp theo ranh giới từ
            if re.search(r'(?<![a-z0-9])' + re.escape(a) + r'(?![a-z0-9])', t):
                found.append((a, self.alias2code[a]))
        # loại trùng code, giữ thứ tự xuất hiện
        seen, res = set(), []
        for a, c in found:
            if c not in seen:
                seen.add(c); res.append(c)
        return res

if __name__ == '__main__':
    here = os.path.dirname(__file__)
    r = BankResolver(os.path.join(here, 'bank_mapping.json'))
    print("Test from_company:", r.from_company("Saigon Hanoi Commercial Joint Stock Bank"))
    print("Test find_in_text 'done SHB 20u':", r.find_in_text("done SHB 20u"))
    print("Test find_in_text 'done vntt klbv nhé':", r.find_in_text("done vntt klbv nhé"))
