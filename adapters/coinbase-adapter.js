const ccxt = require('ccxt');
const dotenv = require('dotenv');

dotenv.config();

/**
 * mapAndExecuteCoinbase - Coinbase Adapter for Unified Trade Schema
 *
 * This adapter facilitates one-click mapping for Coinbase, handling HMAC signing,
 * timestamps, and Advanced Trade v3 endpoints automatically via CCXT.
 *
 * @param {Object} unifiedOrder - The order object conforming to the unified-trade-schema.
 * @param {Object} userConfig - User configuration containing COINBASE_API_KEY and COINBASE_SECRET.
 * @returns {Promise<Object>} - The result from the Coinbase exchange.
 */
async function mapAndExecuteCoinbase(unifiedOrder, userConfig) {
  const exchange = new ccxt.coinbase({
    apiKey: userConfig.COINBASE_API_KEY,
    secret: userConfig.COINBASE_SECRET,
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

module.exports = { mapAndExecuteCoinbase };
