const axios = require('axios');
const dotenv = require('dotenv');

dotenv.config();

/**
 * getXFirehose - Fetches recent tweets from X (Twitter) using the query from the unified feed.
 * GET https://api.x.com/2/tweets/search/recent?query=unifiedFeed.query
 * 
 * @param {Object} unifiedFeed - The unified feed object containing the search query.
 * @param {Object} userConfig - Configuration containing X_BEARER_TOKEN.
 * @returns {Promise<Object>} - The latest tweets and metadata.
 */
async function getXFirehose(unifiedFeed, userConfig) {
  const url = `https://api.x.com/2/tweets/search/recent?query=${encodeURIComponent(unifiedFeed.query)}`;
  const response = await axios.get(url, {
    headers: {
      Authorization: `Bearer ${userConfig.X_BEARER_TOKEN}`,
    },
  });
  // Normalize response
  return {
    source: 'x',
    data: response.data.data || [],
    metadata: response.data.meta || {}
  };
}

/**
 * getFREDIndicator - Fetches economic indicator observations from St. Louis Fed (FRED).
 * GET https://api.stlouisfed.org/fred/series/observations?series_id=unifiedFeed.query&api_key=userConfig.FRED_API_KEY
 * 
 * @param {Object} unifiedFeed - The unified feed object containing the series ID in the query field.
 * @param {Object} userConfig - Configuration containing FRED_API_KEY.
 * @returns {Promise<Object>} - The observations and metadata.
 */
async function getFREDIndicator(unifiedFeed, userConfig) {
  const url = `https://api.stlouisfed.org/fred/series/observations?series_id=${unifiedFeed.query}&api_key=${userConfig.FRED_API_KEY}&file_type=json`;
  const response = await axios.get(url);
  // Normalize response
  return {
    source: 'fred',
    data: response.data.observations || [],
    metadata: {
      realtime_start: response.data.realtime_start,
      realtime_end: response.data.realtime_end,
      count: response.data.count
    }
  };
}

/**
 * getReutersIndicator - Placeholder for Reuters paid endpoint (sentiment/news).
 * @param {Object} unifiedFeed - The unified feed object.
 * @param {Object} userConfig - Configuration for Reuters (REUTERS_APP_KEY, etc.).
 * @returns {Promise<Object>} - Placeholder response.
 */
async function getReutersIndicator(unifiedFeed, userConfig) {
  console.log('Reuters placeholder called for query:', unifiedFeed.query);
  return {
    source: 'reuters',
    status: 'placeholder',
    message: 'Reuters integration requires an enterprise license and institutional partner key.'
  };
}

/**
 * getBloombergIndicator - Placeholder for Bloomberg paid endpoint (economic indicators).
 * @param {Object} unifiedFeed - The unified feed object.
 * @param {Object} userConfig - Configuration for Bloomberg (BLOOMBERG_SERVICE_ID, etc.).
 * @returns {Promise<Object>} - Placeholder response.
 */
async function getBloombergIndicator(unifiedFeed, userConfig) {
  console.log('Bloomberg placeholder called for query:', unifiedFeed.query);
  return {
    source: 'bloomberg',
    status: 'placeholder',
    message: 'Bloomberg Terminal access requires dedicated hardware/license and local B-PIPE server.'
  };
}

/**
 * mapAndExecuteFeeds - Feeds Multi-Adapter for Unified Trade Schema.
 * Dispatches to X, FRED, Reuters, or Bloomberg based on the unifiedFeed.source.
 * 
 * @param {Object} unifiedFeed - The unified feed object.
 * @param {Object} userConfig - Configuration for all supported feeds.
 * @returns {Promise<Object>} - The feed data or placeholder response.
 */
async function mapAndExecuteFeeds(unifiedFeed, userConfig) {
  const source = (unifiedFeed.source || '').toLowerCase();
  
  switch (source) {
    case 'x':
      return getXFirehose(unifiedFeed, userConfig);
    case 'fred':
      return getFREDIndicator(unifiedFeed, userConfig);
    case 'reuters':
      return getReutersIndicator(unifiedFeed, userConfig);
    case 'bloomberg':
      return getBloombergIndicator(unifiedFeed, userConfig);
    default:
      throw new Error(`[Feeds] Unsupported feed source: "${source}". Supported: x, fred, reuters, bloomberg`);
  }
}

module.exports = {
  getXFirehose,
  getFREDIndicator,
  getReutersIndicator,
  getBloombergIndicator,
  mapAndExecuteFeeds
};
