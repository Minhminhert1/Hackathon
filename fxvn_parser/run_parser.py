"""
run_parser.py — Chạy toàn bộ pipeline parser trên file jsonl thu thập được.
Cách dùng:  python run_parser.py <file.jsonl>
Xuất ra: quotes.json, deals.json
"""
import json, sys, os
from bank_resolver import BankResolver
from classify import classify
from deal_matcher import match_deals

def load_and_sort(path):
    rows=[]
    with open(path, encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: rows.append(json.loads(line))
    # sắp theo timestamp, cùng giây theo seq (SỬA lỗi thứ tự cuộn)
    def key(r):
        h,m,s = r['timestamp'].split(':')
        return (r.get('date',''), int(h),int(m),int(s), r.get('seq',0))
    rows.sort(key=key)
    for i,r in enumerate(rows,1): r['order']=i
    return rows

def main(path):
    here=os.path.dirname(os.path.abspath(__file__))
    r=BankResolver(os.path.join(here,'bank_mapping.json'))
    rows=load_and_sort(path)
    for m in rows:
        m['bank_code']=r.from_company(m.get('bank_full','')) or '?'
        m['cls']=classify(m['text'])

    quotes=[{'order':m['order'],'trader':m['sender_name'],'bank':m['bank_code'],
             'side':m['cls'].get('side'),'prices':m['cls'].get('spot_prices'),
             'volume':m['cls'].get('volume'),'text':m['text']}
            for m in rows if m['cls']['type']=='quote_spot']

    deals=match_deals(rows, r)
    spot=[d for d in deals if d['kind']=='spot']
    for d in spot:
        p=d['price_short']
        d['price_full']=(26200+p) if isinstance(p,int) and p<100 else None

    json.dump(quotes,open('quotes.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
    json.dump(spot,open('deals.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

    hi=[d for d in spot if d['confidence']=='high']
    print(f"Đã xử lý {len(rows)} tin.")
    print(f"  Quote spot: {len(quotes)}")
    print(f"  Deal spot:  {len(spot)}  (high={len(hi)}, "
          f"medium={sum(1 for d in spot if d['confidence']=='medium')}, "
          f"low={sum(1 for d in spot if d['confidence']=='low')})")
    print("Xuất: quotes.json, deals.json")

if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else 'FXVN_04-09_sorted.jsonl')
