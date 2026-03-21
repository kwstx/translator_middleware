const axios = require('axios');
const ccxt = require('ccxt');
const path = require('path');

// ── 1. MOCK EXTERNAL DEPENDENCIES ───────────────────────────────

// Mock axios
axios.post = async (url, data, config) => {
    console.log(`\n[MOCK AXIOS POST] URL: ${url}`);
    console.log(`[DATA]:`, JSON.stringify(data, null, 2));
    if (config && config.headers) {
        console.log(`[HEADERS]:`, JSON.stringify(config.headers, null, 2));
    }
    return { data: { status: 'mocked_success', url, data } };
};

axios.get = async (url, config) => {
    console.log(`\n[MOCK AXIOS GET] URL: ${url}`);
    if (config && config.headers) {
        console.log(`[HEADERS]:`, JSON.stringify(config.headers, null, 2));
    }
    return { data: { status: 'mocked_success', url } };
};

// Mock ccxt
class MockExchange {
    constructor(config) {
        this.apiKey = config.apiKey;
        this.secret = config.secret;
        console.log(`[MOCK CCXT] Exchange initialized with key: ${this.apiKey}`);
    }
    async fetchBalance() {
        console.log(`[MOCK CCXT] fetchBalance called`);
        return { total: { BTC: 1.0 } };
    }
    async createOrder(symbol, type, side, amount, price) {
        console.log(`[MOCK CCXT] createOrder called: ${symbol} ${type} ${side} ${amount} @ ${price || 'MARKET'}`);
        return { id: 'mock-order-id', symbol, type, side, amount, price };
    }
}

ccxt.binance = MockExchange;
ccxt.coinbase = MockExchange;

// ── 2. ROUTING HOOK LOGIC (Extracted from mirofish-bridge.ts) ──

const routeTo = async (target, payload, options = {}) => {
    const platform = target.toLowerCase();
    const adapterPath = path.resolve(__dirname, '../../trading-templates/adapters/', `${platform}-adapter.js`);
    console.log(`\n[Engram Router] Routing to platform: ${platform} via ${adapterPath}`);

    const adapter = require(adapterPath);
    
    let methodName = `mapAndExecute${platform.charAt(0).toUpperCase() + platform.slice(1)}`;
    if (platform === 'paypal') methodName = 'mapAndExecutePayPal';

    const result = await adapter[methodName](payload, options);
    console.log(`[Engram Router] Successfully executed ${platform} adapter.`);
    return result;
};

// ── 3. TEST SUITE ───────────────────────────────────────────────

async function runTests() {
    console.log("=== Engram Trading Templates Integration Test (Node.js) ===");

    try {
        // 3.1 Binance Buy Order
        await routeTo('binance', {
            action: 'buy',
            symbol: 'BTC/USDT',
            quantity: 0.005
        }, { BINANCE_API_KEY: 'test_key', BINANCE_SECRET: 'test_secret' });

        // 3.2 Stripe Payment intent
        await routeTo('stripe', {
            amount: 25.0,
            currency: 'usd',
            customerId: 'cus_test_999'
        }, { STRIPE_SECRET_KEY: 'sk_test_mock' });

        // 3.3 Robinhood Buy
        await routeTo('robinhood', {
            action: 'buy',
            symbol: 'ETH-USD',
            quantity: 2.5
        }, { ROBINHOOD_API_KEY: 'mock_key', ROBINHOOD_ACCESS_TOKEN: 'mock_token' });

        // 3.4 Kalshi Bet
        await routeTo('kalshi', {
            symbol: 'FED-2024-HIKE',
            action: 'buy',
            quantity: 50
        }, { KALSHI_TOKEN: 'mock_kalshi_token' });

        // 3.5 PayPal Order
        await routeTo('paypal', {
            amount: 42.0,
            currency: 'usd',
            customerId: 'paypal_user_007'
        }, { PAYPAL_CLIENT_ID: 'p1', PAYPAL_CLIENT_SECRET: 'ps1' });

        // 3.6 Feeds - FRED
        await routeTo('feeds', {
            source: 'fred',
            query: 'UNRATE'
        }, { FRED_API_KEY: 'mock_fred' });

        // 3.7 Feeds - X Search
        await routeTo('feeds', {
            source: 'x',
            query: 'AI Agents'
        }, { X_BEARER_TOKEN: 'mock_x' });


        console.log("\n=== Integration Test PASSED: All adapters verified ===");
    } catch (error) {
        console.error("\n!!! Integration Test FAILED !!!");
        console.error(error);
        process.exit(1);
    }
}

runTests();
