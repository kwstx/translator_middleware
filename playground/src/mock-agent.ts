import { loadEngramConfig } from './engram-sdk'

export type MockAgentConfig = {
  agentId: string
  name: string
  swarmId: string
  mirofishBaseUrl: string
  numAgents: number
  defaultMessage: string
}

const DEFAULT_CONFIG: MockAgentConfig = {
  agentId: 'clawbot-test-001',
  name: 'ClawBot-Alpha',
  swarmId: 'test-swarm-001',
  mirofishBaseUrl: 'http://localhost:5001',
  numAgents: 100,
  defaultMessage:
    'BTC 7-day forecast: assess ETF flow impact and on-chain accumulation ' +
    'patterns. Provide a directional confidence score for execution.',
}

export class MockClawAgent {
  config: MockAgentConfig

  constructor(config: Partial<MockAgentConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }

  private getSdk() {
    return loadEngramConfig({
      enableMiroFishBridge: true,
      mirofishBaseUrl: this.config.mirofishBaseUrl,
      swarmId: this.config.swarmId,
      defaultAgentCount: this.config.numAgents,
    })
  }

  buildSignal(message?: string) {
    return {
      agentId: this.config.agentId,
      name: this.config.name,
      message: message ?? this.config.defaultMessage,
      metadata: {
        swarmId: this.config.swarmId,
        mirofishBaseUrl: this.config.mirofishBaseUrl,
        numAgents: this.config.numAgents,
      },
    }
  }

  async sendToMirofish(message?: string) {
    const sdk = this.getSdk()
    const signal = this.buildSignal(message)
    return sdk.routeTo('mirofish', signal.message, {
      mirofishBaseUrl: signal.metadata.mirofishBaseUrl,
      swarmId: signal.metadata.swarmId,
      defaultAgentCount: signal.metadata.numAgents,
    })
  }
}

export const createMirofishTestAgent = (
  config: Partial<MockAgentConfig> = {},
) => new MockClawAgent(config)
