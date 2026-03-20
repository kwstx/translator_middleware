const axios = require('axios');
const dotenv = require('dotenv');

dotenv.config();

/**
 * mapAndExecuteRobinhood - Robinhood Crypto Adapter for Unified Trade Schema
 *
 * This adapter uses direct axios since CCXT lacks native support for Robinhood Crypto.
 * it maps the unified schema to the Robinhood v2 fee-tier order endpoint with signature headers.
 *
 * @param {Object} unifiedOrder - The order object conforming to the unified-trade-schema.
 * @param {Object} userConfig - User configuration containing ROBINHOOD_API_KEY and ROBINHOOD_ACCESS_TOKEN.
 * @returns {Promise<Object>} - The result from the Robinhood API.
 */
async function mapAndExecuteRobinhood(unifiedOrder, userConfig) {
  const headers = {
    'x-api-key': userConfig.ROBINHOOD_API_KEY,
    'Authorization': `Bearer ${userConfig.ROBINHOOD_ACCESS_TOKEN}`
  };
  const base = 'https://api.robinhood.com/crypto/trading';

  if (unifiedOrder.action === 'buy') {
    return await axios.post(`${base}/orders`, {
      side: 'buy',
      symbol: unifiedOrder.symbol,
      quantity: unifiedOrder.quantity
    }, { headers });
  }
}

module.exports = { mapAndExecuteRobinhood };
