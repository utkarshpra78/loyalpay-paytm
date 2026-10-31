/**
 * API client for Customer App
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

// Get offers for a specific customer
export const getCustomerOffers = (customerId) => 
  fetchAPI(`/customer/${customerId}/offers`);

// Get all active campaigns (for demo - shows all offers)
export const getActiveCampaigns = () => 
  fetchAPI('/customer/offers');

// Redeem an offer
export const redeemOffer = (customerId, campaignId) =>
  fetchAPI(`/customer/${customerId}/redeem/${campaignId}`, { method: 'POST' });

// Get customer profile
export const getCustomerProfile = (customerId) =>
  fetchAPI(`/customer/${customerId}/profile`);

// Poll for new notifications
export const pollNotifications = (customerId, lastCheck) =>
  fetchAPI(`/customer/${customerId}/notifications?since=${lastCheck || ''}`);
