import { useState, useCallback } from 'react';

/**
 * Custom hook for API calls with loading and error states
 */
export function useApi(apiFunction) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err.message || 'An error occurred');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);

  return { data, loading, error, execute };
}

/**
 * Format currency in Indian Rupees
 */
export function formatCurrency(amount) {
  return `₹${amount?.toLocaleString('en-IN') || 0}`;
}

/**
 * Format percentage
 */
export function formatPercent(value) {
  return `${(value * 100).toFixed(0)}%`;
}
