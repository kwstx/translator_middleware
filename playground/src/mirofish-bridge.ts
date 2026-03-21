import axios from 'axios';

/**
 * MiroFish Swarm Bridge for Engram
 * 
 * A self-contained module to pipe inter-agent messages and live external data
 * directly into a running MiroFish swarm simulation.
 * 
 * Usage:
 * const bridge = MiroFishBridge('http://localhost:5001');
 * await bridge.pipe('agent-1', 'A2A', { seed_text: '...', num_agents: 1000 });
 */
export const MiroFishBridge = (baseUrl = 'http://localhost:5001') => {
  /**
   * Pipe data into MiroFish Swarm (Seed Injection)
   * Wraps raw text seeds and optinal agent counts for the MiroFish bridge endpoint.
   */
  const pipe = async (agentId: string, protocol: string, payload: { seed_text: string; num_agents?: number }, swarmId = 'default') => {
    const response = await axios.post(`${baseUrl}/api/v1/mirofish/pipe`, {
      agent_id: agentId,
      protocol: protocol,
      payload: payload,
      swarm_id: swarmId,
    });
    return response.data;
  };

  /**
   * God's Eye Injection
   * Injects live external events (prices, messages, signals) mid-simulation.
   */
  const godsEye = async (swarmId: string, contextObjects: any[]) => {
    const response = await axios.post(`${baseUrl}/api/v1/mirofish/gods-eye`, {
      swarm_id: swarmId,
      context_objects: contextObjects,
    });
    return response.data;
  };

  /**
   * Engram Message Bus Subscriber (Placeholder)
   * This handles inter-agent routing by subscribing to the message bus
   * and piping relevant messages to the swarm.
   */
  const subscribeToRouting = (subscriberUtility: any, agentId: string) => {
    if (!subscriberUtility) {
      console.warn('Engram message bus subscriber utility not found. Please provide one for inter-agent routing.');
      return;
    }

    // Example of how it would hook into an existing subscriber pattern
    subscriberUtility.subscribe(agentId, async (message: any) => {
      console.log(`[MiroFish Bridge] Routing message from ${agentId} to swarm...`);
      await pipe(agentId, message.protocol || 'MCP', {
        seed_text: typeof message.payload === 'string' ? message.payload : JSON.stringify(message.payload),
        num_agents: message.num_agents || 1000
      });
    });
  };

  return {
    pipe,
    godsEye,
    subscribeToRouting,
    baseUrl
  };
};

/**
 * Simulated Engram Connectors
 * In a production environment, these would be imported from your existing integration packages.
 */
export const EngramCCXTWrapper = {
  getCurrentPrices: async (symbols: string[]) => {
    // Simulated real-time price fetch from Binance/Coinbase via CCXT
    return symbols.map(symbol => ({
      symbol,
      price: (Math.random() * 65000 + 1000).toFixed(2),
      currency: 'USD',
      timestamp: new Date().toISOString()
    }));
  }
};

export const XReutersConnector = {
  getSentiment: async (source: 'X' | 'Reuters') => {
    // Simulated sentiment analysis from X firehose or Reuters feed
    const score = (Math.random() * 2 - 1).toFixed(2);
    return {
      source,
      score: parseFloat(score),
      label: score > '0' ? 'Bullish' : 'Bearish',
      confidence: Math.random().toFixed(2)
    };
  }
};

export const InternalNewsAggregator = {
  getRecentHeadlines: async () => {
    // Simulated internal news aggregator
    return [
      "Bitcoin hits new local high amid ETF inflows",
      "Ethereum Shanghai upgrade shows positive network growth",
      "Solana ecosystem expands with new DeFi protocols",
      "Global markets react to latest inflation data"
    ];
  }
};

/**
 * Step 8: Enriched router function with automatic external data ingestion.
 * Automatically fetches fresh live context without requiring extra steps from the calling agent.
 * 
 * @param interAgentMessage - Plain string message from another agent
 * @param targetSwarmId - Swarm identifier for parallel simulations
 * @param numAgents - Number of agents in the swarm (default 1000)
 * @param mirofishBaseUrl - Base URL of the MiroFish service
 * @returns The simulation report forwarded back in a seamless callback
 */
export const pipeToMiroFishSwarm = async (
  interAgentMessage: string, 
  targetSwarmId: string, 
  numAgents = 1000, 
  mirofishBaseUrl = 'http://localhost:5001'
) => {
  // 1. Fetch fresh live context using Engram connectors
  const currentPrices = await EngramCCXTWrapper.getCurrentPrices(['BTC/USD', 'ETH/USD', 'SOL/USD']);
  const xSentiment = await XReutersConnector.getSentiment('X');
  const reutersSentiment = await XReutersConnector.getSentiment('Reuters');
  const latestNewsHeadlines = await InternalNewsAggregator.getRecentHeadlines();

  const externalData = {
    currentPrices,
    sentimentScores: [xSentiment, reutersSentiment],
    latestNewsHeadlines
  };

  // 2. Build the final enriched seedText
  const seedText = `
    [PRIMARY MESSAGE]: ${interAgentMessage}
    
    [LIVE CONTEXT INJECTED]:
    - Market Prices: ${currentPrices.map(p => `${p.symbol}: $${p.price}`).join(', ')}
    - Sentiment (X): ${xSentiment.label} (Score: ${xSentiment.score})
    - Sentiment (Reuters): ${reutersSentiment.label} (Score: ${reutersSentiment.score})
    - News: ${latestNewsHeadlines.slice(0, 3).join(' | ')}
  `.trim();

  // 3. Pipe to MiroFish Swarm Start Endpoint
  const response = await axios.post(`${mirofishBaseUrl}/api/simulation/start`, {
    seedText,
    numAgents,
    swarmId: targetSwarmId,
    godsEyeVariables: externalData
  });

  return response.data;
};

/**
 * -----------------------------------------------------------------
 * Step 9: One-line router integration for OpenClaw / Clawdbot users.
 *
 * Usage:
 *   import { engram } from './mirofish-bridge';
 *   engram.routeTo('mirofish', {
 *     swarmId: 'my-swarm',
 *     mirofishBaseUrl: 'http://localhost:5001',
 *   });
 *
 * PREREQUISITE: users must first launch their own MiroFish instance
 * with a valid LLM_API_KEY configured in its .env file.
 * -----------------------------------------------------------------
 */

export interface MiroFishRouteConfig {
  swarmId?: string;
  mirofishBaseUrl?: string;
  numAgents?: number;
}

export const engram = {
  /**
   * Step 10: Multi-Platform Trading Semantic Templates Integration.
   * Enables one-line activation for Binance, Coinbase, Robinhood, Kalshi, Stripe, PayPal, and Feeds.
   */
  _tradingConfigs: {} as Record<string, any>,

  enableTradingTemplate: (platform: string, config: any) => {
    engram._tradingConfigs[platform.toLowerCase()] = config;
    console.log(`[Engram] Trading template enabled for: ${platform}`);
  },

  /**
   * Route an inter-agent message to the specified target platform.
   *
   * When `target === 'mirofish'`, the message is normalised through the
   * existing translation layer and forwarded to the user's MiroFish
   * instance via `pipeToMiroFishSwarm`.
   *
   * Supported trading platforms: binance, coinbase, robinhood, kalshi, stripe, paypal, feeds.
   *
   * @param target    Target platform identifier (e.g. 'mirofish', 'binance').
   * @param payload   Inter-agent message or structured order payload.
   * @param options   Optional override configuration.
   * @returns         The platform response or simulation report.
   */
  routeTo: async (
    target: string,
    payload: any,
    options: any = {},
  ) => {
    const platform = target.toLowerCase();
    const tradingPlatforms = ['binance', 'coinbase', 'robinhood', 'kalshi', 'stripe', 'paypal', 'feeds'];

    if (platform === 'mirofish') {
      const {
        swarmId = 'default',
        mirofishBaseUrl = 'http://localhost:5001',
        numAgents = 1000,
      } = options;

      const messageStr = typeof payload === 'string' ? payload : JSON.stringify(payload);
      return pipeToMiroFishSwarm(
        messageStr,
        swarmId,
        numAgents,
        mirofishBaseUrl,
      );
    }

    if (tradingPlatforms.includes(platform)) {
      const userConfig = options.apiKey || options.secret ? options : (engram._tradingConfigs[platform] || {});
      
      try {
        let enrichedContext = null;
        if (payload.feedRequest) {
          console.log(`[Engram] Combined payload detected. Enriching from ${payload.feedRequest.source}...`);
          const feedsAdapter = await import(`../../trading-templates/adapters/feeds-adapter.js`);
          enrichedContext = await feedsAdapter.mapAndExecuteFeeds(payload.feedRequest, userConfig);
          console.log(`[Engram] Context enriched with ${enrichedContext.data.length} data points.`);
        }

        /**
         * Dynamic adapter loading. 
         */
        const adapter = await import(`../../trading-templates/adapters/${platform}-adapter.js`);
        
        let methodName = `mapAndExecute${platform.charAt(0).toUpperCase() + platform.slice(1)}`;
        if (platform === 'paypal') methodName = 'mapAndExecutePayPal';

        const rawPayload = payload.tradeOrder || payload;
        const result = await adapter[methodName](rawPayload, userConfig);
        
        console.log(`[Engram] Successfully executed ${platform} trade via unified schema.`);
        
        return {
          status: 'success',
          platform,
          result,
          enrichedContext,
          timestamp: new Date().toISOString()
        };
      } catch (error: any) {
        console.error(`[Engram] Error routing to ${platform} adapter:`, error);
        throw new Error(`[Engram] Failed to execute ${platform} adapter: ${error.message}`);
      }
    }

    throw new Error(
      `[Engram] Unsupported routing target: "${target}". ` +
      `Supported targets: mirofish, ${tradingPlatforms.join(', ')}`,
    );
  },
};

// Export as default for one-line imports
export default MiroFishBridge;
