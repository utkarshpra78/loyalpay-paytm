/**
 * API client for LoyalPay backend
 */

const API_BASE = '/api';

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };
  
  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }
  
  const response = await fetch(url, config);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  
  return response.json();
}

// Simulator endpoints
export const simulateReset = () => fetchAPI('/simulate/reset', { method: 'POST' });

export const simulatePay = (vpa, amount) => 
  fetchAPI('/simulate/pay', { 
    method: 'POST', 
    body: { vpa, amount } 
  });

export const simulateFastForward = (days = 60, seed = 42) =>
  fetchAPI('/simulate/fast-forward', { 
    method: 'POST', 
    body: { days, seed } 
  });

export const simulateNextWeek = (campaignId) =>
  fetchAPI('/simulate/next-week', { 
    method: 'POST', 
    body: { campaign_id: campaignId } 
  });

// Data endpoints
export const getStoreSummary = () => fetchAPI('/store-summary');
export const getSegments = () => fetchAPI('/segments');
export const getCustomers = (segment, limit = 100) => 
  fetchAPI(`/customers?${segment ? `segment=${segment}&` : ''}limit=${limit}`);
export const getInsights = () => fetchAPI('/insights');
export const getAtRisk = () => fetchAPI('/at-risk');

// Campaign endpoints
export const suggestOffer = (budget = 500) => fetchAPI(`/suggest-offer?budget=${budget}`);
export const createCampaign = (budget, name, cashbackPercent = 10, customerIds = null) =>
  fetchAPI('/create-campaign', { 
    method: 'POST', 
    body: { 
      budget, 
      name,
      cashback_percent: cashbackPercent,
      customer_ids: customerIds 
    } 
  });
export const getCampaigns = () => fetchAPI('/campaigns');
export const getCampaignROI = (campaignId) => fetchAPI(`/roi/${campaignId}`);

// Chat endpoint
export const sendChat = (message) =>
  fetchAPI('/chat', { 
    method: 'POST', 
    body: { message } 
  });

// Health check
export const healthCheck = () => fetchAPI('/health');
