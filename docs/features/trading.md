# Trading Semantic Templates

The **Trading Semantic Templates** module provides drop-in, one-click adapters for major crypto exchanges, prediction markets, payment rails, and live data feeds.

---

## 🚀 Overview
It allows agents to route a **single unified payload** across multiple platforms simultaneously without writing custom schema transformations or endpoint-specific code.

| Category | Platforms | Key Integration |
| :--- | :--- | :--- |
| **Crypto** | Binance, Coinbase, Robinhood Crypto | CCXT / Direct REST |
| **Prediction** | Kalshi | Direct REST (trade-api/v2) |
| **Payments** | Stripe, PayPal | Payment Intents / Orders API |
| **Data Feeds** | X (Twitter), FRED, Reuters, Bloomberg | Search & Series APIs |

---

## 🛠️ How It Works
1.  **Unified Schema**: Agents construct a standard `tradeOrder`, `balanceQuery`, `paymentIntent`, or `feedRequest` object.
2.  **Semantic Normalization**: Semantic Bridge maps these fields to the platform's native API (e.g., mapping `quantity` to `amount` or `size` as required).
3.  **Authentication**: Adapters use keys provided in your environment configuration, stored securely and never shared.
4.  **Response Unification**: Heterogeneous responses from different APIs are normalized back into a consistent structure for your agent to parse easily.

---

## 🏗️ Setup & Configuration
1.  **Install**:
    ```bash
    cd trading-templates && npm install
    ```
2.  **Configure `.env`**: Add your API keys for the platforms you intend to use (e.g., `BINANCE_API_KEY`, `KALSHI_TOKEN`, `STRIPE_SECRET_KEY`).
3.  **Enable in SDK**:
    ```ts
    engram.enableTradingTemplate('binance', {
      BINANCE_API_KEY: process.env.BINANCE_API_KEY,
      BINANCE_SECRET: process.env.BINANCE_SECRET,
    });
    ```

---

## 🚀 Usage Examples

### Unified Multi-Platform Order
```ts
// The same object works for both Binance and Coinbase
const order = {
  tradeOrder: { symbol: 'BTC/USDT', action: 'limit', quantity: 0.05, price: 63000 }
};

await engram.routeTo('binance', order);
await engram.routeTo('coinbase', order);
```

### Enriching a Trade with Live Data
```ts
const result = await engram.routeTo('binance', {
  tradeOrder: { symbol: 'ETH/USDT', action: 'market', quantity: 0.5 },
  feedRequest: { source: 'x', query: 'Ethereum sentiment' }
});
```

---

## 🔍 Unified Schema Reference

### `tradeOrder`
- `symbol`: The asset pair (e.g., `BTC/USDT`).
- `action`: `buy`, `sell`, `limit`, `market`, `balance`.
- `quantity`: Amount to trade.
- `price`: Target price for limit orders.

### `paymentIntent`
- `amount`: Transaction value.
- `currency`: ISO code (e.g., `USD`).
- `customerId`: Unique platform identifier.

### `feedRequest`
- `source`: `x`, `fred`, `reuters`, `bloomberg`.
- `query`: Search string or series ID.

---

**Version 0.1.0** | *Trading Semantic Hub*
