const ccxt = require('ccxt');
const dotenv = require('dotenv');

dotenv.config();

/**
 * mapAndExecuteBinance - Binance Adapter for Unified Trade Schema
 *
 * This adapter facilitates one-click mapping for Binance, handling HMAC signing,
 * timestamps, and the base URL (https://api.binance.com) automatically via CCXT.
 *
 * @param {Object} unifiedOrder - The order object conforming to the unified-trade-schema.
 * @param {Object} userConfig - User configuration containing BINANCE_API_KEY and BINANCE_SECRET.
 * @returns {Promise<Object>} - The result from the Binance exchange.
 */
async function mapAndExecuteBinance(unifiedOrder, userConfig) {
  const exchange = new ccxt.binance({
    apiKey: userConfig.BINANCE_API_KEY,
    secret: userConfig.BINANCE_SECRET,
    enableRateLimit: true
  });

  if (unifiedOrder.action === 'balance') {
    return await exchange.fetchBalance();
  }

  return await exchange.createOrder(
    unifiedOrder.symbol,
    unifiedOrder.action.toUpperCase(),
    unifiedOrder.quantity,
    unifiedOrder.price || undefined
  );
}

module.exports = { mapAndExecuteBinance };
