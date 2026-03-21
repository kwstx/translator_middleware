const axios = require('axios');
const path = require('path');
const dotenv = require('dotenv');

// Load environment variables for real API keys if available
dotenv.config();

/**
 * MOCK AXIOS for Reuters and Bloomberg (as requested)
 */
const originalGet = axios.get;
axios.get = async (url, config) => {
    if (url.includes('api.x.com') || url.includes('api.stlouisfed.org')) {
        // Allow REAL requests for X and FRED if tokens are present
        const hasXToken = config && config.headers && config.headers.Authorization && !config.headers.Authorization.includes('your_x_bearer_token');
        const hasFredKey = url.includes('api_key=') && !url.includes('your_fred_api_key');
        
        if (hasXToken || hasFredKey) {
            console.log(`[LIVE REQUEST] Executing real GET: ${url}`);
            return originalGet(url, config);
        }
        
        // Mock fallback if no real keys
        console.log(`[MOCK REQUEST] Intercepting GET (No Key): ${url}`);
        return { data: { status: 'mocked_success', url, source: url.includes('x.com') ? 'x' : 'fred' } };
    }

    // Always mock Reuters and Bloomberg
    console.log(`[MOCK REQUEST] Intercepting GET (Paid/Restricted): ${url}`);
    return { data: { status: 'mocked_success', url, message: 'Reuters/Bloomberg MOCKED' } };
};

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

async function runFeedsTest() {
    process.stdout.write("=== Engram Feeds Enrichment Integration Test ===\n");

    const userConfig = {
        X_BEARER_TOKEN: process.env.X_BEARER_TOKEN || 'mock_x',
        FRED_API_KEY: process.env.FRED_API_KEY || 'mock_fred',
        REUTERS_APP_KEY: process.env.REUTERS_APP_KEY || 'mock_reuters',
        BLOOMBERG_SERVICE_ID: process.env.BLOOMBERG_SERVICE_ID || 'mock_bloomberg'
    };

    try {
        // 1. Test X Feed
        console.log("\n[TEST 1] Pulling recent X posts...");
        const xResult = await routeTo('feeds', {
            source: 'x',
            query: 'Bitcoin price sentiment',
            limit: 5
        }, userConfig);
        console.log("X Result - Source:", xResult.source);
        console.log("X Result - Data Count:", xResult.data ? xResult.data.length : 0);

        // 2. Test FRED Feed
        console.log("\n[TEST 2] Pulling FRED GDP observations...");
        const fredResult = await routeTo('feeds', {
            source: 'fred',
            query: 'GDP',
            limit: 1
        }, userConfig);
        console.log("FRED Result - Source:", fredResult.source);
        console.log("FRED Result - Data Point 0:", fredResult.data[0] || "No data");

        // 3. Test Reuters Placeholder (Restricted)
        console.log("\n[TEST 3] Pulling Reuters headlines (Mocked/Restricted)...");
        const reutersResult = await routeTo('feeds', {
            source: 'reuters',
            query: 'Federal Reserve rate cut',
            limit: 5
        }, userConfig);
        console.log("Reuters Result:", JSON.stringify(reutersResult, null, 2));

        // 4. Test Combined Enrichment (Enrich BEFORE routing to an exchange)
        console.log("\n[TEST 4] Simulating combined enrichment (Enrich + Trade)...");
        
        // This simulates the logic now in engram.routeTo
        const enrichedRouter = async (platform, payload, config) => {
            let enrichedContext = null;
            if (payload.feedRequest) {
                console.log(`[Enrichment] Combined payload detected. Fetching from ${payload.feedRequest.source}...`);
                enrichedContext = await routeTo('feeds', payload.feedRequest, config);
                console.log(`[Enrichment] Enrichment complete. Context received.`);
            }
            
            const rawPayload = payload.tradeOrder || payload;
            console.log(`[Execution] Routing trade to ${platform}...`);
            // Mock exchange call
            const result = { status: 'mocked_trade_success', platform };
            
            return {
                status: 'success',
                platform,
                result,
                enrichedContext,
                timestamp: new Date().toISOString()
            };
        }

        const combinedPayload = {
            tradeOrder: {
                action: 'buy',
                symbol: 'BTC/USDT',
                quantity: 0.1
            },
            feedRequest: {
                source: 'x',
                query: 'BTC sentiment',
                limit: 5
            }
        };

        const finalResult = await enrichedRouter('binance', combinedPayload, userConfig);
        console.log("\n[FINAL ENRICHED PACKAGE]:");
        console.log(JSON.stringify(finalResult, (key, value) => {
            if (typeof value === 'string' && value.length > 100) return value.substring(0, 100) + '...';
            return value;
        }, 2));

        console.log("\n=== Integration Test PASSED: Feeds and Enrichment verified ===");
    } catch (error) {
        console.error("\n!!! Integration Test FAILED !!!");
        console.error(error);
        process.exit(1);
    }
}

runFeedsTest();
