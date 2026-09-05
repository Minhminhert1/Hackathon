import os
import sys

# Kich hoat mau sac ANSI va tieng Viet co dau tren Windows
os.system('')
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import re
import asyncio
from datetime import datetime, time
from typing import List, Dict, Any, Union, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# =========================================================================
# CAU HINH HE THONG
# =========================================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Thoi gian theo doi Heartbeat (canh bao khi khong co tin moi)
HEARTBEAT_TIMEOUT_MINUTES = 30   # Canh bao neu qua 30 phut khong co tin
WORK_HOURS_START = time(8, 30)    # Bat dau khung gio theo doi: 8h30
WORK_HOURS_END = time(16, 0)      # Ket thuc khung gio theo doi: 16h00

# Bo nho theo doi trong ngay
seen_message_ids = set()
total_today_count = 0
today_rooms_count = {}
last_active_room = None
last_message_time = None
last_heartbeat_alert_time = None
unsaved_buffer = []  # Bo nho tam khi file bi khoa boi Word/Excel

def get_today_file_path() -> str:
    today_str = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(DATA_DIR, f'data-{today_str}.jsonl')

def load_existing_ids():
    global total_today_count, last_message_time
    today_file = get_today_file_path()
    if os.path.exists(today_file):
        try:
            with open(today_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        mid = record.get('message_id')
                        if mid:
                            seen_message_ids.add(mid)
                            total_today_count += 1
                            today_rooms_count['FXVN'] = today_rooms_count.get('FXVN', 0) + 1
                        cap = record.get('captured_at')
                        if cap:
                            try:
                                clean_cap = cap.replace('Z', '').split('+')[0]
                                dt = datetime.fromisoformat(clean_cap)
                                if not last_message_time or dt > last_message_time:
                                    last_message_time = dt
                            except Exception:
                                pass
                    except Exception:
                        pass
            print(f'[*] Da nap lai {len(seen_message_ids)} tin nhan FXVN da luu hom nay tu file: {os.path.basename(today_file)}')
        except Exception as e:
            print(f'[!] Loi khi doc du lieu cu: {e}')
    
    if not last_message_time:
        last_message_time = datetime.now()

def clean_whitespace(text: Optional[str]) -> str:
    if not text:
        return ''
    cleaned = re.sub(r'[ \t]+', ' ', text)
    lines = [line.strip() for line in cleaned.splitlines()]
    return '\n'.join([l for l in lines if l]).strip()

def clean_name(text: Optional[str]) -> str:
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip()

def print_heartbeat_alert(mins_elapsed: int, is_test: bool = False):
    red_color = '\033[91m\033[1m'
    reset_color = '\033[0m'
    now_str = datetime.now().strftime('%H:%M:%S')
    last_str = last_message_time.strftime('%H:%M:%S') if last_message_time else 'Chua co tin nao'
    
    test_tag = ' [TEST KIEM TRA]' if is_test else ''
    banner = (
        f'\n{red_color}'
        f'********************************************************************************\n'
        f'⚠️  CẢNH BÁO{test_tag}: ĐÃ {mins_elapsed} PHÚT KHÔNG CÓ TIN NHẮN MỚI NÀO!\n'
        f'   - Thời gian nhận tin gần nhất : {last_str}\n'
        f'   - Thời gian hiện tại         : {now_str}\n'
        f'   - Khung giờ giám sát        : {WORK_HOURS_START.strftime("%H:%M")} - {WORK_HOURS_END.strftime("%H:%M")}\n'
        f'   👉 Vui lòng kiểm tra: Tab chat Refinitiv còn mở không, mạng còn kết nối không?\n'
        f'********************************************************************************\n'
        f'{reset_color}'
    )
    print(banner)

def flush_unsaved_buffer():
    global unsaved_buffer
    if not unsaved_buffer:
        return
    today_file = get_today_file_path()
    try:
        with open(today_file, 'a', encoding='utf-8') as f:
            for record in unsaved_buffer:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            f.flush()
        print(f'\n✅ [ĐÃ XỬ LÝ] Đã ghi thành công {len(unsaved_buffer)} tin tạm từ bộ nhớ vào file (sau khi mở khóa Word)!')
        unsaved_buffer = []
    except PermissionError:
        pass
    except Exception as e:
        print(f'[!] Loi khi ghi buffer: {e}')

async def heartbeat_monitor():
    global last_heartbeat_alert_time
    while True:
        await asyncio.sleep(5)
        # Thu ghi lai cac tin ton trong bo nho dem neu file da duoc mo khoa
        flush_unsaved_buffer()
        
        now = datetime.now()
        # Chi kiem tra trong khung gio 8h30 den 16h00
        if WORK_HOURS_START <= now.time() <= WORK_HOURS_END:
            lm = last_message_time
            if lm and lm.tzinfo is not None:
                lm = lm.replace(tzinfo=None)
            diff_seconds = (now - lm).total_seconds() if lm else 0
            threshold_seconds = HEARTBEAT_TIMEOUT_MINUTES * 60
            
            if diff_seconds >= threshold_seconds:
                if not last_heartbeat_alert_time or (now - last_heartbeat_alert_time).total_seconds() >= 300:
                    last_heartbeat_alert_time = now
                    mins = int(diff_seconds // 60)
                    print_heartbeat_alert(mins)

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_existing_ids()
    monitor_task = asyncio.create_task(heartbeat_monitor())
    yield
    monitor_task.cancel()

app = FastAPI(title='FX Collector Server', lifespan=lifespan)

# Cho phep Chrome Private Network Access (PNA) ket noi
@app.middleware("http")
async def add_pna_headers(request: Request, call_next):
    origin = request.headers.get("origin", "*")
    if request.method == "OPTIONS":
        res = Response(status_code=200)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "*"
        res.headers["Access-Control-Allow-Credentials"] = "true"
        res.headers["Access-Control-Allow-Private-Network"] = "true"
        return res

    res = await call_next(request)
    res.headers["Access-Control-Allow-Origin"] = origin
    res.headers["Access-Control-Allow-Private-Network"] = "true"
    return res

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class RawMessage(BaseModel):
    message_id: str
    sender_name: Optional[str] = ''
    bank_full: Optional[str] = ''
    timestamp: Optional[str] = ''
    date: Optional[str] = ''
    text: Optional[str] = ''
    room_name: Optional[str] = ''
    direction: Optional[str] = 'incoming'
    seq: Optional[int] = 0
    captured_at: Optional[str] = None

class BatchPayload(BaseModel):
    messages: List[RawMessage]

@app.get('/')
def health_check():
    lm = last_message_time
    if lm and lm.tzinfo is not None:
        lm = lm.replace(tzinfo=None)
    last_str = lm.strftime('%Y-%m-%d %H:%M:%S') if lm else None
    return {
        'status': 'ok',
        'message': 'FX Collector Server dang hoat dong tot!',
        'today_total': total_today_count,
        'today_rooms': today_rooms_count,
        'last_active_room': last_active_room,
        'unique_ids_seen': len(seen_message_ids),
        'unsaved_buffer_count': len(unsaved_buffer),
        'last_message_time': last_str,
        'heartbeat_monitoring': f'{WORK_HOURS_START.strftime("%H:%M")} - {WORK_HOURS_END.strftime("%H:%M")} (nguong: {HEARTBEAT_TIMEOUT_MINUTES} phut)',
        'dashboard_url': 'http://localhost:8000/status'
    }

@app.get('/status', response_class=HTMLResponse)
def status_dashboard():
    now = datetime.now()
    lm = last_message_time
    if lm and lm.tzinfo is not None:
        lm = lm.replace(tzinfo=None)
        
    last_str = lm.strftime('%H:%M:%S (%d/%m/%Y)') if lm else 'Chưa có tin nào'
    
    diff_desc = ''
    if lm:
        diff_sec = int((now - lm).total_seconds())
        if diff_sec < 0:
            diff_sec = 0
        if diff_sec < 60:
            diff_desc = f'Cách đây {diff_sec} giây'
        elif diff_sec < 3600:
            diff_desc = f'Cách đây {diff_sec // 60} phút'
        else:
            diff_desc = f'Cách đây {diff_sec // 3600} giờ {(diff_sec % 3600) // 60} phút'

    today_filename = os.path.basename(get_today_file_path())
    
    buffer_warning = ''
    if len(unsaved_buffer) > 0:
        buffer_warning = f'<div style="background: #b45309; padding: 12px; border-radius: 8px; margin-bottom: 15px; text-align: center; color: #fff; font-weight: bold;">⚠️ File đang bị Word/Excel khóa! Đang giữ {len(unsaved_buffer)} tin tạm trong bộ nhớ. Hãy ĐÓNG Word/Excel lại.</div>'

    html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="5">
  <title>Bảng Trạng Thái FX Collector</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      margin: 0;
      padding: 30px 15px;
      display: flex;
      justify-content: center;
    }}
    .container {{
      max-width: 650px;
      width: 100%;
    }}
    .header {{
      text-align: center;
      margin-bottom: 25px;
    }}
    .header h1 {{
      margin: 0 0 10px 0;
      font-size: 26px;
      color: #38bdf8;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 16px;
      border-radius: 20px;
      background: #065f46;
      color: #34d399;
      font-weight: bold;
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin-bottom: 20px;
    }}
    .card {{
      background: #1e293b;
      padding: 22px 15px;
      border-radius: 12px;
      border: 1px solid #334155;
      text-align: center;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }}
    .card-full {{
      grid-column: span 2;
      text-align: left;
      padding: 20px;
    }}
    .card-title {{
      color: #94a3b8;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.5px;
      margin-bottom: 10px;
    }}
    .card-value {{
      font-size: 36px;
      font-weight: 800;
      color: #38bdf8;
    }}
    .card-sub {{
      color: #94a3b8;
      font-size: 13px;
      margin-top: 6px;
    }}
    .info-row {{
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #334155;
      font-size: 14px;
    }}
    .info-row:last-child {{
      border-bottom: none;
    }}
    .info-label {{
      color: #94a3b8;
    }}
    .info-value {{
      color: #f1f5f9;
      font-weight: 600;
    }}
    .footer {{
      text-align: center;
      color: #64748b;
      font-size: 13px;
      margin-top: 25px;
    }}
    .btn-refresh {{
      background: #0284c7;
      color: white;
      border: none;
      padding: 8px 18px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      margin-top: 10px;
      transition: 0.2s;
    }}
    .btn-refresh:hover {{
      background: #0369a1;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🚀 Bảng Trạng Thái FX Collector</h1>
      <span class="badge">🟢 ĐANG THU THẬP NHÓM FXVN</span>
    </div>
    
    {buffer_warning}

    <div class="grid">
      <div class="card">
        <div class="card-title">TỔNG SỐ TIN FXVN HÔM NAY</div>
        <div class="card-value">{total_today_count:,}</div>
        <div class="card-sub">tin nhắn FXVN đã lưu an toàn</div>
      </div>
      
      <div class="card">
        <div class="card-title">NHẬN TIN GẦN NHẤT</div>
        <div class="card-value" style="font-size: 24px; color: #a78bfa; margin-top: 6px;">{last_str.split(' ')[0]}</div>
        <div class="card-sub" style="color: #34d399; font-weight: 500;">{diff_desc}</div>
      </div>

      <div class="card card-full">
        <div class="card-title" style="margin-bottom: 12px;">CHI TIẾT VẬN HÀNH</div>
        <div class="info-row">
          <span class="info-label">💬 Nhóm chat mục tiêu:</span>
          <span class="info-value" style="color: #34d399; font-size: 15px;">FXVN (Chỉ thu thập FXVN)</span>
        </div>
        <div class="info-row">
          <span class="info-label">📁 File lưu trữ hôm nay:</span>
          <span class="info-value" style="color: #38bdf8;">{today_filename}</span>
        </div>
        <div class="info-row">
          <span class="info-label">🛡️ Khung giờ giám sát Heartbeat:</span>
          <span class="info-value">08:30 - 16:00 (Cảnh báo khi &gt; 30 phút)</span>
        </div>
        <div class="info-row">
          <span class="info-label">⏱️ Tự động làm mới trang:</span>
          <span class="info-value">Mỗi 5 giây</span>
      </div>
    </div>

    <div class="footer">
      Trang tự động cập nhật số liệu mỗi 5 giây.<br>
      <button class="btn-refresh" onclick="location.reload()">🔄 Bấm để làm mới ngay</button>
    </div>
  </div>
</body>
</html>'''
    return HTMLResponse(content=html)

@app.get('/test-heartbeat')
def test_heartbeat():
    print_heartbeat_alert(HEARTBEAT_TIMEOUT_MINUTES, is_test=True)
    return {
        'status': 'ok',
        'message': f'Da in thu canh bao DO ({HEARTBEAT_TIMEOUT_MINUTES} phut) ra man hinh server!',
        'monitoring_window': f'{WORK_HOURS_START.strftime("%H:%M")} - {WORK_HOURS_END.strftime("%H:%M")}',
        'timeout_minutes': HEARTBEAT_TIMEOUT_MINUTES
    }

@app.post('/api/messages')
@app.post('/messages')
async def receive_messages(payload: Union[BatchPayload, List[RawMessage], RawMessage]):
    global total_today_count, last_message_time, last_heartbeat_alert_time, last_active_room
    now = datetime.now()
    last_message_time = now
    last_heartbeat_alert_time = None
    
    items: List[RawMessage] = []
    if isinstance(payload, BatchPayload):
        items = payload.messages
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, RawMessage):
        items = [payload]
        
    if not items:
        return {'status': 'ok', 'saved': 0, 'duplicates': 0, 'today_total': total_today_count, 'today_rooms': today_rooms_count}

    new_saved = 0
    duplicates = 0
    today_file = get_today_file_path()
    
    try:
        with open(today_file, 'a', encoding='utf-8') as f:
            # Ghi truoc cac tin ton trong bo nho dem (neu co)
            for r in unsaved_buffer:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
            unsaved_buffer.clear()

            for item in items:
                mid = item.message_id.strip() if item.message_id else ''
                if not mid:
                    continue
                    
                if mid in seen_message_ids:
                    duplicates += 1
                    continue
                    
                seen_message_ids.add(mid)
                total_today_count += 1
                new_saved += 1
                today_rooms_count['FXVN'] = total_today_count
                last_active_room = 'FXVN'
                
                record = {
                    'message_id': mid,
                    'sender_name': clean_name(item.sender_name),
                    'bank_full': clean_name(item.bank_full),
                    'timestamp': clean_name(item.timestamp),
                    'date': clean_name(item.date),
                    'text': clean_whitespace(item.text),
                    'room_name': 'FXVN',
                    'direction': item.direction or 'incoming',
                    'seq': item.seq if item.seq is not None else total_today_count,
                    'captured_at': item.captured_at or now.isoformat()
                }
                
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            f.flush()
    except PermissionError:
        # File dang bi khoa boi Word/Excel! Luu tam vao bo nho dem
        for item in items:
            mid = item.message_id.strip() if item.message_id else ''
            if not mid or mid in seen_message_ids:
                if mid in seen_message_ids:
                    duplicates += 1
                continue
            seen_message_ids.add(mid)
            total_today_count += 1
            new_saved += 1
            today_rooms_count['FXVN'] = total_today_count
            last_active_room = 'FXVN'
            record = {
                'message_id': mid,
                'sender_name': clean_name(item.sender_name),
                'bank_full': clean_name(item.bank_full),
                'timestamp': clean_name(item.timestamp),
                'date': clean_name(item.date),
                'text': clean_whitespace(item.text),
                'room_name': 'FXVN',
                'direction': item.direction or 'incoming',
                'seq': item.seq if item.seq is not None else total_today_count,
                'captured_at': item.captured_at or now.isoformat()
            }
            unsaved_buffer.append(record)
        print('\n⚠️  [CẢNH BÁO] File data-xxxx.jsonl đang bị mở bởi Microsoft Word / Excel!')
        print('   Vui lòng ĐÓNG Word/Excel lại. Các tin nhắn đang được giữ an toàn trong bộ nhớ đệm.')

    time_str = now.strftime('%H:%M:%S')
    last_str = last_message_time.strftime('%H:%M:%S')
    print(f'[{time_str}] Nhận lô: +{new_saved} tin mới nhóm [FXVN] (bỏ qua {duplicates} tin trùng). Tổng cộng FXVN hôm nay: {total_today_count} tin | Nhận gần nhất lúc: {last_str}')
    
    return {
        'status': 'ok',
        'saved': new_saved,
        'duplicates': duplicates,
        'today_total': total_today_count,
        'today_rooms': today_rooms_count,
        'buffered': len(unsaved_buffer),
        'last_message_time': last_str
    }

if __name__ == '__main__':
    import uvicorn
    print('=' * 60)
    print('   FX COLLECTOR SERVER - DANG CHAY')
    print('   Dia chi kiem tra: http://localhost:8000')
    print('   Trang xem trang thai: http://localhost:8000/status')
    print('   Du lieu luu tai thu muc: data/')
    print(f'   Giam sat Heartbeat: {WORK_HOURS_START.strftime("%H:%M")} - {WORK_HOURS_END.strftime("%H:%M")} (nguong {HEARTBEAT_TIMEOUT_MINUTES} phut)')
    print('   (Nhan Ctrl + C de dung server)')
    print('=' * 60)
    uvicorn.run(app, host='127.0.0.1', port=8000)
