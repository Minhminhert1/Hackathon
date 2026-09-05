// =========================================================================
// TEST SCRIPT FOR FXVN DEDICATED COLLECTOR
// =========================================================================

(function() {
  'use strict';

  const cfg = window.FX_CONFIG || FX_CONFIG;
  const seenMessageIds = new Set();
  let currentSeq = 0;
  const pendingQueue = [];

  function isViewingFXVN() {
    // 1. Check treeWalker for header containing "Participants"
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
            return false;
          }
        }
      }
    }

    // 2. Check element with text "FXVN" located in header area (top < 150px, left > 200px)
    const allEls = document.querySelectorAll('*');
    for (const el of allEls) {
      if (el.children.length === 0 && (el.textContent || '').trim() === 'FXVN') {
        const r = el.getBoundingClientRect();
        if (r.top < 150 && r.left > 200) {
          return true;
        }
      }
    }

    // 3. Check selected sidebar item
    const selected = document.querySelector('[aria-selected="true"], [class*="selected" i]');
    if (selected) {
      return (selected.textContent || '').includes('FXVN');
    }

    return true;
  }

  function processMessageElement(msgEl) {
    if (!msgEl || msgEl.nodeType !== Node.ELEMENT_NODE) return;

    // Chi bat tin khi dang xem phong FXVN!
    if (!isViewingFXVN()) {
      return;
    }

    let messageId = msgEl.getAttribute(cfg.ATTRIBUTES.MESSAGE_ID);
    if (!messageId) return;
    if (seenMessageIds.has(messageId)) return;
    seenMessageIds.add(messageId);
    currentSeq++;

    const roomName = 'FXVN';
    const senderName = msgEl.getAttribute(cfg.ATTRIBUTES.SENDER_NAME) || '';
    const company = msgEl.getAttribute(cfg.ATTRIBUTES.COMPANY) || '';
    const timestamp = msgEl.getAttribute(cfg.ATTRIBUTES.TIMESTAMP) || '';
    const contentEl = msgEl.querySelector(cfg.SELECTORS.MESSAGE_CONTENT);
    const text = contentEl ? contentEl.textContent : msgEl.textContent;

    console.log(`[FX Collector] Bắt tin #${currentSeq} | Phòng: "${roomName}" | ${senderName} (${company}) [${timestamp}]: "${text}"`);
  }

  window.isViewingFXVN = isViewingFXVN;
  window.processMessageElement = processMessageElement;

  const messages = document.querySelectorAll(cfg.SELECTORS.MESSAGE_ITEM);
  messages.forEach(processMessageElement);
})();
