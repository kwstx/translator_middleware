import { pipeToMiroFishSwarm } from './mirofish-bridge';

export interface EngramSDKConfig {
  enableMiroFishBridge?: boolean;
  mirofishBaseUrl?: string;
  swarmId?: string;
  defaultAgentCount?: number;
}

export interface MiroFishRouteOptions {
  mirofishBaseUrl?: string;
  swarmId?: string;
  defaultAgentCount?: number;
}

export type EngramAdapter = (
  message: string,
  options?: MiroFishRouteOptions,
) => Promise<unknown>;

export interface EngramSDK {
  adapters: Record<string, EngramAdapter>;
  tradingTemplates: {
    platforms: string[];
    enable: (platform: string, config: any) => void;
    getConfigs: () => Record<string, any>;
  };
  routeTo: (
    target: string,
    message: string,
    options?: MiroFishRouteOptions,
  ) => Promise<unknown>;
}

const DEFAULT_SWARM_ID = 'default';
const DEFAULT_AGENT_COUNT = 1000;

const requireMiroFishBaseUrl = (baseUrl?: string) => {
  if (!baseUrl) {
    throw new Error(
      '[Engram] enableMiroFishBridge requires `mirofishBaseUrl` ' +
        'to be set in the SDK config.',
    );
  }
  return baseUrl;
};

export const loadEngramConfig = (config: EngramSDKConfig = {}): EngramSDK => {
  const adapters: Record<string, EngramAdapter> = {};

  if (config.enableMiroFishBridge) {
    const baseUrl = requireMiroFishBaseUrl(config.mirofishBaseUrl);
    const baseSwarmId = config.swarmId ?? DEFAULT_SWARM_ID;
    const baseAgentCount = config.defaultAgentCount ?? DEFAULT_AGENT_COUNT;

    adapters.mirofish = async (
      message: string,
      options: MiroFishRouteOptions = {},
    ) => {
      const resolvedBaseUrl = requireMiroFishBaseUrl(
        options.mirofishBaseUrl ?? baseUrl,
      );
      const resolvedSwarmId = options.swarmId ?? baseSwarmId;
      const resolvedAgentCount =
        options.defaultAgentCount ?? baseAgentCount;

      return pipeToMiroFishSwarm(
        message,
        resolvedSwarmId,
        resolvedAgentCount,
        resolvedBaseUrl,
      );
    };
  }

  const tradingConfigs: Record<string, any> = {};
  const tradingTemplates = {
    platforms: ['binance', 'coinbase', 'robinhood', 'kalshi', 'stripe', 'paypal', 'feeds'],
    enable: (platform: string, config: any) => {
      tradingConfigs[platform.toLowerCase()] = config;
    },
    getConfigs: () => tradingConfigs,
  };

  return {
    adapters,
    tradingTemplates,
    routeTo: async (
      target: string,
      message: string,
      options?: MiroFishRouteOptions,
    ) => {
      const platform = target.toLowerCase();
      if (tradingTemplates.platforms.includes(platform)) {
        const userConfig = options?.apiKey || options?.secret ? options : (tradingConfigs[platform] || {});
        
        // Dynamic import logic (simulated for browser environment)
        console.log(`[Engram] Routing to trading template: ${platform}`);
        
        // This would call the backend or a library that handles the heavy lifting
        // For the playground, we can simulate the call or use the bridge
        if (config.enableMiroFishBridge) {
          return adapters.mirofish(message, { ...options, ...userConfig });
        }
        
        return { status: 'simulated', platform, message: 'Trading template routed' };
      }

      const adapter = adapters[platform];
      if (!adapter) {
        throw new Error(
          `[Engram] Unsupported adapter: "${target}". ` +
            `Available adapters: ${Object.keys(adapters).join(', ') || 'none'}`,
        );
      }
      return adapter(message, options);
    },
  };
};

