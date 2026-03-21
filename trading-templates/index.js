const { mapAndExecuteBinance } = require('./adapters/binance-adapter');
const { mapAndExecuteCoinbase } = require('./adapters/coinbase-adapter');
const { mapAndExecuteKalshi } = require('./adapters/kalshi-adapter');
const { mapAndExecutePaypal } = require('./adapters/paypal-adapter');
const { mapAndExecuteRobinhood } = require('./adapters/robinhood-adapter');
const { mapAndExecuteStripe } = require('./adapters/stripe-adapter');
const { mapAndExecuteFeeds } = require('./adapters/feeds-adapter');

module.exports = {
  binance: mapAndExecuteBinance,
  coinbase: mapAndExecuteCoinbase,
  kalshi: mapAndExecuteKalshi,
  paypal: mapAndExecutePaypal,
  robinhood: mapAndExecuteRobinhood,
  stripe: mapAndExecuteStripe,
  feeds: mapAndExecuteFeeds
};
