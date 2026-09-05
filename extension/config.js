// =========================================================================
// FILE CAU HINH CHO EXTENSION FX COLLECTOR
// =========================================================================

window.FX_CONFIG = {
  // Dia chi server Python (dung 127.0.0.1 de tranh loi phan giai IPv6 tren Windows)
  SERVER_URL: 'http://127.0.0.1:8000/api/messages',

  // Khoang thoi gian gom tin (3 giay)
  BATCH_INTERVAL_MS: 3000,

  // Cac bo dinh vi tren giao dien chat Refinitiv
  SELECTORS: {
    // Khung chua toan bo chat
    CONVERSATION_CONTAINER: '#conversation-container',

    // The chua tin nhan (bat ca incoming, outgoing va the co data-message-id)
    MESSAGE_ITEM: 'div[class*="incoming-message"], div[class*="outgoing-message"], [data-message-id]',

    // The con chua noi dung
    MESSAGE_CONTENT: '[data-testid="parsed-raw-message"]',

    // The chua ten phong chat
    ROOM_NAME: '[class*="ChatroomName"]',
  },

  // Cac thuoc tinh du lieu tren the
  ATTRIBUTES: {
    MESSAGE_ID: 'data-message-id',
    SENDER_NAME: 'data-sender-name',
    COMPANY: 'data-company',
    TIMESTAMP: 'data-timestamp',
    DATE: 'data-date',
  }
};

var FX_CONFIG = window.FX_CONFIG;
