import React, { useState, useEffect } from 'react';
import { ArrowLeft, Send, Check, ChevronDown, ChevronUp, Gift, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function OffersPage({ atRiskCustomers, onCreateCampaign, onBack, loading, isLostPage = false }) {
  const [cashbackPercent, setCashbackPercent] = useState(10);
  const [selectedCustomers, setSelectedCustomers] = useState(new Set());
  const [showCustomerList, setShowCustomerList] = useState(true);
  const [selectAll, setSelectAll] = useState(false);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [redemptions, setRedemptions] = useState([]);
  const [stats, setStats] = useState(null);
  const [wonBackCustomers, setWonBackCustomers] = useState([]);
  const [sendingToWonBack, setSendingToWonBack] = useState(null); // customer_id being sent to
  const [wonBackCashback, setWonBackCashback] = useState(10);

  // Poll for redemptions and won-back customers
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch redemptions
        const redemptionsRes = await fetch(`${API_BASE}/merchant/redemptions`);
        if (redemptionsRes.ok) {
          const data = await redemptionsRes.json();
          setRedemptions(data.redemptions || []);
          setStats(data.stats || null);
        }
        
        // Fetch won-back customers
        const wonBackRes = await fetch(`${API_BASE}/won-back`);
        if (wonBackRes.ok) {
          const data = await wonBackRes.json();
          setWonBackCustomers(data.customers || []);
        }
      } catch (error) {
        // Silent fail
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  // Filter out won-back customers from at-risk list (in case backend hasn't updated yet)
  const wonBackIds = new Set(wonBackCustomers.map(c => c.customer_id));
  const filteredAtRiskCustomers = (atRiskCustomers || []).filter(c => !wonBackIds.has(c.customer_id));
  
  const sortedCustomers = [...filteredAtRiskCustomers].sort(
    (a, b) => (b.churn_probability || 0) - (a.churn_probability || 0)
  );

  const handleSend = async () => {
    if (selectedCustomers.size === 0) return;
    
    setSending(true);
    try {
      await onCreateCampaign(cashbackPercent, Array.from(selectedCustomers));
      setResult('success');
      setSelectedCustomers(new Set());
      setSelectAll(false);
    } catch (error) {
      setResult('error');
    }
    setSending(false);
    
    setTimeout(() => setResult(null), 3000);
  };

  const handleSendToWonBack = async (customerId) => {
    setSending(true);
    try {
      await onCreateCampaign(wonBackCashback, [customerId]);
      setResult('success');
      setSendingToWonBack(null);
    } catch (error) {
      setResult('error');
    }
    setSending(false);
    
    setTimeout(() => setResult(null), 3000);
  };

  const toggleCustomer = (customerId) => {
    const newSelected = new Set(selectedCustomers);
    if (newSelected.has(customerId)) {
      newSelected.delete(customerId);
    } else {
      newSelected.add(customerId);
    }
    setSelectedCustomers(newSelected);
    setSelectAll(newSelected.size === sortedCustomers.length);
  };

  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedCustomers(new Set());
    } else {
      setSelectedCustomers(new Set(sortedCustomers.map(c => c.customer_id)));
    }
    setSelectAll(!selectAll);
  };

  return (
    <div className="min-h-full">
      {/* Header */}
      <div className="section">
        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <ArrowLeft size={20} style={{ color: 'var(--text-primary)' }} />
          </button>
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>Send Cashback Offers</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              {sortedCustomers.length} {isLostPage ? 'lost' : 'at-risk'} customers
            </div>
          </div>
        </div>
      </div>

      {/* Campaign Stats (if any) */}
      {stats && stats.total_redemptions > 0 && (
        <>
          <div className="section">
            <div className="section-header">
              <span className="section-title">Campaign Results</span>
            </div>
            <div style={{ padding: '16px', display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Recovered</div>
                <div className="amount-md tabular-nums" style={{ color: 'var(--green)' }}>
                  ₹{stats.total_revenue_from_redemptions?.toFixed(0)}
                </div>
              </div>
              <div style={{ width: '1px', background: 'var(--divider)' }} />
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Redemptions</div>
                <div className="amount-md tabular-nums">
                  {stats.total_redemptions}/{stats.total_offers_sent}
                </div>
              </div>
              <div style={{ width: '1px', background: 'var(--divider)' }} />
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Cashback</div>
                <div className="amount-md tabular-nums" style={{ color: 'var(--amber)' }}>
                  -₹{stats.total_discount_given?.toFixed(0)}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Won Back Customers Section */}
      {wonBackCustomers.length > 0 && (
        <div className="section">
          <div className="section-header">
            <span className="section-title">Won Back Customers</span>
            <span style={{ fontSize: '11px', color: 'var(--green)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '6px', height: '6px', background: 'var(--green)', borderRadius: '50%' }} />
              {wonBackCustomers.length} recovered
            </span>
          </div>
          
          {wonBackCustomers.map((customer) => (
            <div key={customer.customer_id}>
              <div className="list-row" style={{ padding: '12px 16px' }}>
                <div style={{ 
                  width: '36px', 
                  height: '36px', 
                  borderRadius: '50%', 
                  background: 'var(--green-bg)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  marginRight: '12px'
                }}>
                  <Check size={18} style={{ color: 'var(--green)' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: '600', fontSize: '14px' }}>{customer.customer_label}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    {customer.total_redemptions} redemption{customer.total_redemptions > 1 ? 's' : ''} · ₹{customer.total_spent?.toFixed(0)} spent · saved ₹{customer.total_saved?.toFixed(0)}
                  </div>
                </div>
                <button
                  onClick={() => setSendingToWonBack(sendingToWonBack === customer.customer_id ? null : customer.customer_id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '16px',
                    border: '1px solid var(--accent)',
                    background: sendingToWonBack === customer.customer_id ? 'var(--accent)' : 'transparent',
                    color: sendingToWonBack === customer.customer_id ? 'white' : 'var(--accent)',
                    fontSize: '12px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Gift size={14} />
                  {sendingToWonBack === customer.customer_id ? 'Cancel' : 'New Offer'}
                </button>
              </div>
              
              {/* Inline Send Offer Section */}
              {sendingToWonBack === customer.customer_id && (
                <div style={{ 
                  padding: '16px', 
                  background: 'var(--bg-page)', 
                  borderBottom: '1px solid var(--divider)'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    marginBottom: '12px'
                  }}>
                    <span style={{ fontWeight: '600', fontSize: '13px' }}>
                      Send Offer to {customer.customer_label}
                    </span>
                    <button
                      onClick={() => setSendingToWonBack(null)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                    >
                      <X size={16} style={{ color: 'var(--text-muted)' }} />
                    </button>
                  </div>
                  
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      Select Cashback:
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {[5, 10, 15, 20, 25].map((percent) => (
                        <button
                          key={percent}
                          onClick={() => setWonBackCashback(percent)}
                          style={{
                            flex: 1,
                            padding: '8px 0',
                            borderRadius: '6px',
                            border: '1px solid',
                            borderColor: wonBackCashback === percent ? 'var(--accent)' : 'var(--divider)',
                            background: wonBackCashback === percent ? 'var(--accent)' : 'var(--bg-surface)',
                            color: wonBackCashback === percent ? 'white' : 'var(--text-primary)',
                            fontWeight: '600',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          {percent}%
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleSendToWonBack(customer.customer_id)}
                    disabled={sending}
                    style={{
                      width: '100%',
                      padding: '10px',
                      borderRadius: '8px',
                      border: 'none',
                      background: 'var(--accent)',
                      color: 'white',
                      fontWeight: '600',
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    <Send size={14} />
                    {sending ? 'Sending...' : `Send ${wonBackCashback}% Cashback Offer`}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Spacer if won-back section exists */}
      {wonBackCustomers.length > 0 && <div className="spacer" />}

      {/* Cashback Percentage */}
      <div className="section">
        <div className="section-header">
          <span className="section-title">{isLostPage ? 'Win Back Lost Customers' : 'Cashback Offer'}</span>
        </div>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            {[5, 10, 15, 20, 25].map((percent) => (
              <button
                key={percent}
                onClick={() => setCashbackPercent(percent)}
                style={{
                  flex: 1,
                  padding: '12px 0',
                  borderRadius: '8px',
                  border: '1px solid',
                  borderColor: cashbackPercent === percent ? 'var(--accent)' : 'var(--divider)',
                  background: cashbackPercent === percent ? 'var(--accent)' : 'var(--bg-surface)',
                  color: cashbackPercent === percent ? 'white' : 'var(--text-primary)',
                  fontWeight: '600',
                  fontSize: '14px',
                  cursor: 'pointer'
                }}
              >
                {percent}%
              </button>
            ))}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '8px', textAlign: 'center' }}>
            Customers pay {100 - cashbackPercent}% on their next visit
          </div>
        </div>
      </div>

      {/* Customer Selection */}
      <div className="section">
        <button
          onClick={() => setShowCustomerList(!showCustomerList)}
          className="section-header"
          style={{ width: '100%', cursor: 'pointer', background: 'none', border: 'none', textAlign: 'left' }}
        >
          <span className="section-title">Select Customers</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--accent)', fontWeight: '500' }}>
              {selectedCustomers.size} selected
            </span>
            {showCustomerList ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </button>

        {showCustomerList && (
          <>
            {/* Select All */}
            <button
              onClick={toggleSelectAll}
              className="list-row"
              style={{ cursor: 'pointer', width: '100%', textAlign: 'left', background: 'var(--bg-page)' }}
            >
              <div style={{ flex: 1, fontWeight: '500', fontSize: '13px' }}>Select all</div>
              <div className={`checkbox ${selectAll ? 'checked' : ''}`}>
                {selectAll && <Check size={14} />}
              </div>
            </button>

            {/* Customer List */}
            {sortedCustomers.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                  {wonBackCustomers.length > 0 
                    ? `All ${isLostPage ? 'lost' : 'at-risk'} customers have been won back! 🎉`
                    : `No ${isLostPage ? 'lost' : 'at-risk'} customers. Load demo data first.`}
                </div>
              </div>
            ) : (
              sortedCustomers.map((customer) => (
                <button
                  key={customer.customer_id}
                  onClick={() => toggleCustomer(customer.customer_id)}
                  className="list-row"
                  style={{ cursor: 'pointer', width: '100%', textAlign: 'left' }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '500', fontSize: '13px' }}>{customer.label}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                      {customer.recency_days}d ago · ₹{customer.monetary_avg?.toFixed(0)} avg
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ 
                      fontSize: '12px', 
                      fontWeight: '500',
                      color: (customer.churn_probability || 0) > 0.6 ? 'var(--red)' : 'var(--amber)'
                    }}>
                      {((customer.churn_probability || 0) * 100).toFixed(0)}% risk
                    </span>
                    <div className={`checkbox ${selectedCustomers.has(customer.customer_id) ? 'checked' : ''}`}>
                      {selectedCustomers.has(customer.customer_id) && <Check size={14} />}
                    </div>
                  </div>
                </button>
              ))
            )}
          </>
        )}
      </div>

      {/* Send Button */}
      {selectedCustomers.size > 0 && (
        <div style={{ padding: '16px', background: 'var(--bg-page)' }}>
          <button
            onClick={handleSend}
            disabled={sending}
            className="btn-primary"
          >
            {sending ? (
              'Sending...'
            ) : (
              <>
                <Send size={18} />
                Send to {selectedCustomers.size} customers
              </>
            )}
          </button>
        </div>
      )}

      {/* Result Toast */}
      {result === 'success' && (
        <div className="toast" style={{ background: 'var(--green)' }}>
          Offers sent successfully!
        </div>
      )}

      <div style={{ height: '16px' }} />
    </div>
  );
}
