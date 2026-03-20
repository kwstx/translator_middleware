const axios = require('axios');

/**
 * mapAndExecuteKalshi - Kalshi Prediction Market Adapter for Unified Trade Schema
 *
 * This adapter uses axios to interact with the Kalshi trade-api/v2.
 * It maps the unified tradeOrder object to place bets on events.
 *
 * @param {Object} unifiedOrder - The order object conforming to the unified-trade-schema.
 * @param {Object} userConfig - User configuration containing KALSHI_TOKEN.
 * @returns {Promise<Object>} - The result from the Kalshi API.
 */
async function mapAndExecuteKalshi(unifiedOrder, userConfig) {
  const headers = { Authorization: `Bearer ${userConfig.KALSHI_TOKEN}` };
  return await axios.post('/markets/orders', {
    ticker: unifiedOrder.symbol,
    side: unifiedOrder.action,
    count: unifiedOrder.quantity
  }, {
    headers,
    baseURL: 'https://api.elections.kalshi.com/trade-api/v2'
  });
}

module.exports = { mapAndExecuteKalshi };
