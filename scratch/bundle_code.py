import os

project_dir = r'C:\Users\HOANG MINH\Desktop\fx-collector'
output_file = os.path.join(project_dir, 'FX_COLLECTOR_CODEBASE.md')

files_to_bundle = [
    ('requirements.txt', 'txt', 'File thu vien Python can cai dat'),
    ('run_server.bat', 'bat', 'File khoi dong Server bang 1 cu dup chuot'),
    (os.path.join('extension', 'manifest.json'), 'json', 'File cau hinh tien ich Chrome (Manifest V3)'),
    (os.path.join('extension', 'config.js'), 'javascript', 'File cau hinh tham so va bo dinh vi DOM'),
    (os.path.join('extension', 'content.js'), 'javascript', 'Content Script chay tren Refinitiv Messenger de bat tin DOM'),
    ('server.py', 'python', 'FastAPI Backend Server luu tru du lieu, Heartbeat va Dashboard'),
]

sample_data = '{"message_id": "new:mcr:5T5sHaNAfCfn7AJ9vz93W:3f15c5fb-49ef-40e3-a3b6-f102cd445d44", "sender_name": "Huan Tran Nguyen Khiem", "bank_full": "Indovina Bank Ltd", "timestamp": "16:57:49", "date": "4/9/2026", "text": "MSBI pm pls", "room_name": "FXVN", "direction": "incoming", "seq": 1, "captured_at": "2026-09-04T17:18:03.500Z"}'

content = []
content.append('# 📦 TOÀN BỘ MÃ NGUỒN DỰ ÁN FX COLLECTOR (DÀNH CHO REVIEW)')
content.append('')
content.append('> **Mô tả dự án:** Công cụ thu thập dữ liệu tin nhắn chat theo thời gian thực từ giao diện Refinitiv Workspace Messenger (nền tảng web tại `https://messenger.refinitiv.com/messenger/`).')
content.append('> ')
content.append('> **Kiến trúc gồm 2 phần:**')
content.append('> 1. **Chrome Extension (Manifest V3):** Inject `content.js` vào Refinitiv Messenger, dùng `MutationObserver` theo dõi DOM container `#conversation-container`, trích xuất tin nhắn (`incoming` và `outgoing`), chống trùng bằng `data-message-id`, đệm tin và gửi định kỳ 3 giây/lô về local server.')
content.append('> 2. **Python Server (FastAPI + Uvicorn):** Lắng nghe tại `http://127.0.0.1:8000/api/messages`, ghi dữ liệu UTF-8 vào file `.jsonl` theo ngày (`data/data-YYYY-MM-DD.jsonl`), có cơ chế bộ nhớ đệm `unsaved_buffer` chống lỗi khóa file của Windows (khi mở Excel/Word), trang dashboard thời gian thực tại `http://localhost:8000/status`, và hệ thống giám sát Heartbeat cảnh báo đỏ trong khung giờ 08:30 - 16:00 nếu quá 30 phút không có tin.')
content.append('')
content.append('---')
content.append('')

for rel_path, lang, desc in files_to_bundle:
    full_path = os.path.join(project_dir, rel_path)
    content.append(f'## 📄 File: `{rel_path.replace(chr(92), "/")}`')
    content.append(f'*{desc}*')
    content.append('')
    content.append(f'```{lang}')
    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
        content.append(f.read().rstrip())
    content.append('```')
    content.append('')
    content.append('---')
    content.append('')

content.append('## 📊 Mẫu dữ liệu lưu trữ (`data/data-YYYY-MM-DD.jsonl`)')
content.append('Mỗi dòng là 1 JSON Object hoàn chỉnh (UTF-8 không BOM):')
content.append('```json')
content.append(sample_data)
content.append('```')
content.append('')

full_text = '\n'.join(content)
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f'Done. Created {output_file} with {len(full_text)} characters.')
