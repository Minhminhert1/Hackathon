// =========================================================================
// SCRIPT CHINH CUA EXTENSION FX COLLECTOR
// Chuyen biet thu thap tin nhan cho nhom FXVN (Refinitiv Messenger)
// =========================================================================

(function() {
  'use strict';

  const cfg = window.FX_CONFIG || FX_CONFIG;
  console.log('%c[FX Collector] Tiện ích FXVN Collector đã sẵn sàng!', 'color: #00ff00; font-weight: bold; font-size: 13px;');

  const seenMessageIds = new Set();
  let currentSeq = 0;
  const pendingQueue = [];
  let isSending = false;

  let currentObservedContainer = null;
  let containerObserver = null;
  let wasFXVN = null;

  // Kiem tra xem nguoi dung co dang mo phong FXVN hay khong
  function isViewingFXVN() {
    // 1. Kiem tra the chu "Participants" o thanh tieu de phong chat
    try {
      const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        const text = node.nodeValue || '';
        if (/\b\d+\s+participants\b/i.test(text)) {
          const header = node.parentElement?.closest('header, [class*="header" i], [class*="Header"]') || 
                         node.parentElement?.parentElement;
          if (header) {
            const headerText = header.textContent || '';
            if (headerText.includes('FXVN')) {
              return true;
            } else {
              // Dang o phong khac (vi du MSB Swap) -> bo qua
              return false;
            }
          }
        }
      }
    } catch (e) {}

    // 2. Kiem tra the chu "FXVN" nam o vung tieu de phia tren (top < 150px, left > 180px)
    try {
      const allEls = document.querySelectorAll('*');
      for (const el of allEls) {
        if (el.children.length === 0 && (el.textContent || '').trim() === 'FXVN') {
          const r = el.getBoundingClientRect();
          if (r.top < 150 && r.left > 180) {
            return true;
          }
        }
      }
    } catch (e) {}

    // 3. Kiem tra muc dang duoc chon tren thanh danh sach ben trai
    try {
      const selected = document.querySelector('[aria-selected="true"], [class*="selected" i]');
      if (selected) {
        const selText = selected.textContent || '';
        if (selText.includes('FXVN')) return true;
        if (selText.includes('MSB') || selText.includes('Swap')) return false;
      }
    } catch (e) {}

    // Mac dinh coi nhu dang o FXVN
    return true;
  }

  // Theo doi trang thai phong FXVN
  function checkFXVNStatus() {
    const isFXVN = isViewingFXVN();
    if (isFXVN !== wasFXVN) {
      if (isFXVN) {
        console.log('%c[FX Collector] 🟢 Đang xem nhóm FXVN - Tự động thu thập tin!', 'color: #00ff00; font-weight: bold; font-size: 13px;');
        scanVisibleMessages();
      } else {
        console.log('%c[FX Collector] ⏸️ Đang xem nhóm khác - Tạm ngưng bắt tin để đảm bảo chỉ lưu dữ liệu FXVN.', 'color: #ffd700; font-weight: bold;');
      }
      wasFXVN = isFXVN;
    }
  }

  // Ham gui lo tin ve server
  async function flushBatch() {
    if (pendingQueue.length === 0 || isSending) return;

    isSending = true;
    const batchToSend = [...pendingQueue];

    const targetUrls = [
      cfg.SERVER_URL || 'http://127.0.0.1:8000/api/messages',
      'http://127.0.0.1:8000/api/messages',
      'http://localhost:8000/api/messages'
    ];

    let success = false;
    for (const url of Array.from(new Set(targetUrls))) {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ messages: batchToSend })
        });

        if (response.ok) {
          pendingQueue.splice(0, batchToSend.length);
          console.log(`%c[FX Collector] Đã gửi thành công lô ${batchToSend.length} tin FXVN về server. Tổng đã bắt: ${seenMessageIds.size}`, 'color: #98fb98; font-weight: bold;');
          success = true;
          break;
        }
      } catch (err) {}
    }

    if (!success) {
      console.log('[FX Collector] Server đang khởi động hoặc chưa sẵn sàng, các tin vẫn được giữ an toàn trong bộ nhớ.');
    }
    isSending = false;
  }

  // Hen gio gui tin
  let sendTimeout = null;
  function scheduleSend() {
    if (sendTimeout) clearTimeout(sendTimeout);
    sendTimeout = setTimeout(flushBatch, 1500);
  }

  // Ham trich xuat du lieu tu the tin nhan
  function processMessageElement(msgEl) {
    if (!msgEl || msgEl.nodeType !== Node.ELEMENT_NODE) return;

    // Chi thu thap khi dang o nhom FXVN!
    if (!isViewingFXVN()) {
      return;
    }

    // Tim ma tin nhan
    let messageId = msgEl.getAttribute(cfg.ATTRIBUTES.MESSAGE_ID);
    if (!messageId) {
      const childWithId = msgEl.querySelector(`[${cfg.ATTRIBUTES.MESSAGE_ID}]`);
      if (childWithId) messageId = childWithId.getAttribute(cfg.ATTRIBUTES.MESSAGE_ID);
    }
    if (!messageId) {
      const parentWithId = msgEl.closest(`[${cfg.ATTRIBUTES.MESSAGE_ID}]`);
      if (parentWithId) messageId = parentWithId.getAttribute(cfg.ATTRIBUTES.MESSAGE_ID);
    }

    if (!messageId) return;

    // Chống trùng lặp
    if (seenMessageIds.has(messageId)) return;
    seenMessageIds.add(messageId);
    currentSeq++;

    // Xac dinh chieu tin nhan: incoming hay outgoing
    let direction = 'incoming';
    const cls = (msgEl.className || '') + ' ' + (msgEl.parentElement?.className || '');
    if (cls.includes('outgoing') || msgEl.getAttribute('data-direction') === 'outgoing') {
      direction = 'outgoing';
    }

    // Lay cac thuoc tinh
    const senderName = msgEl.getAttribute(cfg.ATTRIBUTES.SENDER_NAME) || 
                       msgEl.querySelector(`[${cfg.ATTRIBUTES.SENDER_NAME}]`)?.getAttribute(cfg.ATTRIBUTES.SENDER_NAME) || 
                       (direction === 'outgoing' ? 'Tôi' : '');
    const company = msgEl.getAttribute(cfg.ATTRIBUTES.COMPANY) || 
                    msgEl.querySelector(`[${cfg.ATTRIBUTES.COMPANY}]`)?.getAttribute(cfg.ATTRIBUTES.COMPANY) || '';
    const timestamp = msgEl.getAttribute(cfg.ATTRIBUTES.TIMESTAMP) || 
                      msgEl.querySelector(`[${cfg.ATTRIBUTES.TIMESTAMP}]`)?.getAttribute(cfg.ATTRIBUTES.TIMESTAMP) || '';
    const date = msgEl.getAttribute(cfg.ATTRIBUTES.DATE) || 
                 msgEl.querySelector(`[${cfg.ATTRIBUTES.DATE}]`)?.getAttribute(cfg.ATTRIBUTES.DATE) || '';

    // Lay noi dung tin nhan (chu + emoji)
    const contentEl = msgEl.querySelector(cfg.SELECTORS.MESSAGE_CONTENT);
    const text = contentEl ? (contentEl.textContent || '') : (msgEl.textContent || '');

    const record = {
      message_id: messageId,
      sender_name: senderName,
      bank_full: company,
      timestamp: timestamp,
      date: date,
      text: text,
      room_name: 'FXVN',
      direction: direction,
      seq: currentSeq,
      captured_at: new Date().toISOString()
    };

    pendingQueue.push(record);

    const dirBadge = direction === 'outgoing' ? '📤 GỬI ĐI' : '📥 ĐẾN';
    console.log(
      `%c[FX Collector] Bắt tin #${currentSeq} [${dirBadge}] | FXVN | ${senderName} (${company}) [${timestamp}]: "${text.substring(0, 35)}..."`,
      direction === 'outgoing' ? 'color: #ffd700; font-weight: bold;' : 'color: #00bfff; font-weight: bold;'
    );

    scheduleSend();
  }

  // Quet toan bo tin dang hien thi tren man hinh
  function scanVisibleMessages() {
    if (!isViewingFXVN()) return;
    try {
      const messages = document.querySelectorAll(cfg.SELECTORS.MESSAGE_ITEM);
      if (messages && messages.length > 0) {
        messages.forEach(processMessageElement);
      }
    } catch (e) {}
  }

  // Xu ly khi co phan tu moi them vao DOM (MutationObserver)
  function handleMutations(mutations) {
    if (!isViewingFXVN()) return;
    for (const mutation of mutations) {
      if (!mutation.addedNodes) continue;
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;

        if (node.matches && (node.matches(cfg.SELECTORS.MESSAGE_ITEM) || node.hasAttribute(cfg.ATTRIBUTES.MESSAGE_ID))) {
          processMessageElement(node);
        }

        if (node.querySelectorAll) {
          const children = node.querySelectorAll(cfg.SELECTORS.MESSAGE_ITEM);
          for (const child of children) {
            processMessageElement(child);
          }
        }
      }
    }
  }

  // Gan MutationObserver vao khung tin nhan
  function checkAndBindContainer() {
    const container = document.querySelector(cfg.SELECTORS.CONVERSATION_CONTAINER) || 
                      document.querySelector('[id*="conversation-container"]');
    if (!container) return;

    if (container !== currentObservedContainer || !container.isConnected) {
      if (containerObserver) {
        containerObserver.disconnect();
      }

      currentObservedContainer = container;
      containerObserver = new MutationObserver(handleMutations);
      containerObserver.observe(container, { childList: true, subtree: true });

      console.log('%c[FX Collector] Đã gắn theo dõi vào khung chat thành công!', 'color: #32cd32; font-weight: bold;');
      if (isViewingFXVN()) {
        scanVisibleMessages();
      }
    }
  }

  // Dinh ky gui tin moi 3 giay
  setInterval(flushBatch, cfg.BATCH_INTERVAL_MS);

  // Vong lap dinh ky kiem tra container, trang thai FXVN va quet tin moi 1.5 giay
  setInterval(() => {
    checkAndBindContainer();
    checkFXVNStatus();
    if (isViewingFXVN()) {
      scanVisibleMessages();
    }
  }, 1500);

  function start() {
    const rootTarget = document.body || document.documentElement;
    if (rootTarget) {
      const rootObserver = new MutationObserver(() => {
        checkAndBindContainer();
        checkFXVNStatus();
      });
      rootObserver.observe(rootTarget, { childList: true, subtree: true });
    }
    checkAndBindContainer();
    checkFXVNStatus();
    if (isViewingFXVN()) {
      scanVisibleMessages();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
