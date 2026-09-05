// =========================================================================
// TEST CONTENT SCRIPT FOR MULTIROOM
// =========================================================================

(function() {
  'use strict';

  const cfg = window.FX_CONFIG || FX_CONFIG;
  const seenMessageIds = new Set();
  let currentSeq = 0;
  const pendingQueue = [];

  // Ham lam sach ten phong chat
  function cleanRoomName(text) {
    if (!text) return '';
    let name = text.replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
    // Loai bo chuoi "N Participants" hoac "Participants..."
    name = name.replace(/\s*\(\d+\s*participants?\)/i, '');
    name = name.replace(/\s*\d+\s*participants?.*$/i, '');
    name = name.replace(/\s*participants?.*$/i, '');
    // Loai bo so badge don le o cuoi (neu co)
    name = name.replace(/\s+\d{1,3}$/, '');
    return name.trim();
  }

  // Ham xac dinh chinh xac phong chat dang mo (Active Room)
  function getActiveRoomName() {
    // 1. Uu tien 1: Tim tu khu vuc Header ngay tren conversation-container
    try {
      const container = document.querySelector(cfg.SELECTORS.CONVERSATION_CONTAINER) || 
                        document.querySelector('[id*="conversation-container"]');
      if (container) {
        let parent = container.parentElement;
        for (let i = 0; i < 5 && parent; i++) {
          const header = parent.querySelector('header, [class*="ConversationHeader"], [class*="conversation-header"], [class*="ChatHeader"], [class*="chat-header"], [class*="Header"], [data-testid*="header"]');
          if (header && !header.contains(container)) {
            const titleEl = header.querySelector('[class*="ChatroomName"], [class*="room-name" i], [class*="channel-name" i], [class*="title" i], [class*="Title"], h1, h2, h3');
            if (titleEl && !/participant/i.test(titleEl.textContent)) {
              const res = cleanRoomName(titleEl.textContent);
              if (res && res.length > 1) return res;
            }
            const match = (header.textContent || '').trim().match(/^(.*?)(?:\s+\d+\s+participants|\s+participants)/i);
            if (match && cleanRoomName(match[1])) {
              return cleanRoomName(match[1]);
            }
          }
          parent = parent.parentElement;
        }
      }
    } catch (e) {}

    // 2. Uu tien 2: Tim the co chu "Participants" dac trung cua phong Refinitiv Messenger
    try {
      const allEls = document.querySelectorAll('*');
      for (const el of allEls) {
        if (el.children.length <= 1 && /\b\d+\s+participants\b/i.test(el.textContent || '')) {
          const p = el.parentElement;
          if (p) {
            const titleEl = p.querySelector('[class*="ChatroomName"], [class*="title" i], [class*="Title"], [class*="name" i]');
            if (titleEl && titleEl !== el) {
              const res = cleanRoomName(titleEl.textContent);
              if (res && res.length > 1) return res;
            }
            for (const child of p.children) {
              if (child !== el && !child.textContent.toLowerCase().includes('participant')) {
                const txt = cleanRoomName(child.textContent);
                if (txt && txt.length > 1 && txt.length < 60) return txt;
              }
            }
            const match = (p.textContent || '').trim().match(/^(.*?)(?:\s+\d+\s+participants)/i);
            if (match && cleanRoomName(match[1])) {
              return cleanRoomName(match[1]);
            }
          }
        }
      }
    } catch (e) {}

    // 3. Uu tien 3: Tab dang chon hoac muc dang active tren thanh ben (Sidebar)
    try {
      const activeSelectors = [
        '[aria-selected="true"] [class*="ChatroomName"]',
        '[class*="selected" i] [class*="ChatroomName"]',
        '[class*="active" i] [class*="ChatroomName"]',
        '[class*="current" i] [class*="ChatroomName"]',
        '[data-is-selected="true"] [class*="ChatroomName"]',
        '[data-selected="true"] [class*="ChatroomName"]',
        '[role="tab"][aria-selected="true"]',
        '[role="tab"][class*="active" i]',
        '[role="tab"][class*="selected" i]',
        '[aria-selected="true"]',
        '[class*="selected" i][class*="channel" i]',
        '[class*="active" i][class*="channel" i]'
      ];
      for (const sel of activeSelectors) {
        const activeEl = document.querySelector(sel);
        if (activeEl) {
          const nameEl = activeEl.querySelector('[class*="ChatroomName"], [class*="name" i]') || activeEl;
          const res = cleanRoomName(nameEl.textContent);
          if (res && res.length > 1 && res.length < 60) return res;
        }
      }
    } catch (e) {}

    // 4. Uu tien 4: The ChatroomName nam o khung chinh (khong phai thanh sidebar ben trai)
    try {
      const allNames = document.querySelectorAll(cfg.SELECTORS.ROOM_NAME || '[class*="ChatroomName"]');
      for (const el of allNames) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && rect.left > 200 && rect.top < 150) {
          const res = cleanRoomName(el.textContent);
          if (res && res.length > 1) return res;
        }
      }
    } catch (e) {}

    // 5. Uu tien 5: Du phong
    try {
      const allNames = document.querySelectorAll(cfg.SELECTORS.ROOM_NAME || '[class*="ChatroomName"]');
      if (allNames.length === 1) {
        return cleanRoomName(allNames[0].textContent);
      }
    } catch (e) {}

    return '';
  }

  function processMessageElement(msgEl) {
    if (!msgEl || msgEl.nodeType !== Node.ELEMENT_NODE) return;
    let messageId = msgEl.getAttribute(cfg.ATTRIBUTES.MESSAGE_ID);
    if (!messageId) return;
    if (seenMessageIds.has(messageId)) return;
    seenMessageIds.add(messageId);
    currentSeq++;

    const roomName = getActiveRoomName();
    const senderName = msgEl.getAttribute(cfg.ATTRIBUTES.SENDER_NAME) || '';
    const company = msgEl.getAttribute(cfg.ATTRIBUTES.COMPANY) || '';
    const timestamp = msgEl.getAttribute(cfg.ATTRIBUTES.TIMESTAMP) || '';
    const contentEl = msgEl.querySelector(cfg.SELECTORS.MESSAGE_CONTENT);
    const text = contentEl ? contentEl.textContent : msgEl.textContent;

    console.log(`[FX Collector] Bắt tin #${currentSeq} | Phòng: "${roomName}" | ${senderName} (${company}) [${timestamp}]: "${text}"`);
  }

  window.processMessageElement = processMessageElement;
  const messages = document.querySelectorAll(cfg.SELECTORS.MESSAGE_ITEM);
  messages.forEach(processMessageElement);
})();
