import { engram } from '../../playground/src/mirofish-bridge';
import axios from 'axios';
import ccxt from 'ccxt';

// ── 1. MOCK EXTERNAL DEPENDENCIES ───────────────────────────────

// Mock axios
const mockAxios = {
    post: async (url: string, data: any, config: any) => {
        console.log(`[MOCK AXIOS POST] URL: ${url}`);
        console.log(`[MOCK AXIOS POST] DATA:`, JSON.stringify(data, null, 2));
        return { data: { status: 'mocked_success', url, data } };
    },
    get: async (url: string, config: any) => {
        console.log(`[MOCK AXIOS GET] URL: ${url}`);
        return { data: { status: 'mocked_success', url } };
    }
};

// @ts-ignore
axios.post = mockAxios.post;
// @ts-ignore
axios.get = mockAxios.get;

// Mock ccxt
class MockExchange {
    apiKey: string = '';
    secret: string = '';
    constructor(config: any) {
        this.apiKey = config.apiKey;
        this.secret = config.secret;
    }
    async fetchBalance() {
        console.log(`[MOCK CCXT] fetchBalance called`);
        return { total: { BTC: 1.0 } };
    }
    async createOrder(symbol: string, type: string, side: string, amount: number, price?: number) {
        console.log(`[MOCK CCXT] createOrder called: ${symbol} ${type} ${side} ${amount} @ ${price || 'MARKET'}`);
        return { id: 'mock-order-id', symbol, type, side, amount, price };
    }
}

// @ts-ignore
ccxt.binance = MockExchange;
// @ts-ignore
ccxt.coinbase = MockExchange;

// ── 2. TEST SUITE ───────────────────────────────────────────────

async function runTests() {
    console.log("--- Starting Trading Templates E2E Test Suite ---");

    const testKeys = {
        apiKey: 'test_api_key',
        secret: 'test_secret'
    };

    // 2.1 Binance Buy Order
    console.log("\n[TEST] Binance Buy Order...");
    await engram.routeTo('binance', {
        action: 'buy',
        symbol: 'BTC/USDT',
        quantity: 0.1
    }, testKeys);

    // 2.2 Stripe Payment Intent
    console.log("\n[TEST] Stripe Payment Intent...");
    await engram.routeTo('stripe', {
        amount: 50.0,
        currency: 'usd',
        customerId: 'cus_test_123'
    }, { STRIPE_SECRET_KEY: 'sk_test_mock' });

    // 2.3 Kalshi Bet
    console.log("\n[TEST] Kalshi Bet...");
    await engram.routeTo('kalshi', {
        symbol: 'PRES-2024-TRUMP',
        action: 'buy',
        quantity: 100
    }, { KALSHI_TOKEN: 'mock_token' });

    // 2.4 PayPal Order
    console.log("\n[TEST] PayPal Order...");
    await engram.routeTo('paypal', {
        amount: 15.99,
        currency: 'usd',
        customerId: 'user_456'
    }, { PAYPAL_CLIENT_ID: 'mock_id', PAYPAL_CLIENT_SECRET: 'mock_secret' });

    // 2.5 FEEDS: FRED Indicator
    console.log("\n[TEST] Feeds FRED Indicator...");
    await engram.routeTo('feeds', {
        source: 'fred',
        query: 'GDP',
        limit: 1
    }, { FRED_API_KEY: 'mock_fred_key' });

    // 2.6 FEEDS: X Firehose
    console.log("\n[TEST] Feeds X Firehose...");
    await engram.routeTo('feeds', {
        source: 'x',
        query: 'Engram AI',
        limit: 10
    }, { X_BEARER_TOKEN: 'mock_x_token' });

    console.log("\n--- All Trading Template Tests Completed ---");
}

runTests().catch(err => {
    console.error("Test suite failed:", err);
    process.exit(1);
});
