module.exports = {
  tradeOrder: {
    action: 'buy | sell | market | limit',
    symbol: 'string',
    quantity: 'number',
    price: 'optional number',
    side: 'buy | sell'
  },
  balanceQuery: {
    asset: 'string'
  },
  paymentIntent: {
    amount: 'number',
    currency: 'usd',
    customerId: 'optional string'
  },
  feedRequest: {
    source: 'x | fred | reuters',
    query: 'string',
    limit: 'number'
  },
  feedResponse: {
    source: 'string',
    data: 'array',
    metadata: 'object'
  }
};
