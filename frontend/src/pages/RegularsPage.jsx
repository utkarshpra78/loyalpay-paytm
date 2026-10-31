import React, { useState } from 'react';
import { ArrowLeft, Search, ChevronDown } from 'lucide-react';

export default function RegularsPage({ customers, onBack, loading }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('frequency');

  const filteredCustomers = (customers || [])
    .filter(c => c.label.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'frequency') return b.frequency - a.frequency;
      if (sortBy === 'monetary') return b.monetary_avg - a.monetary_avg;
      if (sortBy === 'recency') return a.recency_days - b.recency_days;
      return 0;
    });

  const regularCustomers = filteredCustomers.filter(c => c.is_regular);

  return (
    <div className="min-h-full">
      {/* Header */}
      <div className="section">
        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <ArrowLeft size={20} style={{ color: 'var(--text-primary)' }} />
          </button>
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>Regular Customers</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              {regularCustomers.length} customers with 2+ visits
            </div>
          </div>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="section">
        <div style={{ padding: '12px 16px' }}>
          <div style={{ position: 'relative' }}>
            <Search 
              size={18} 
              style={{ 
                position: 'absolute', 
                left: '12px', 
                top: '50%', 
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)'
              }} 
            />
            <input
              type="text"
              placeholder="Search by ID (e.g. #A12)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input"
              style={{ paddingLeft: '40px' }}
            />
          </div>
          
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
            <SortButton 
              active={sortBy === 'frequency'} 
              onClick={() => setSortBy('frequency')}
              label="Visits"
            />
            <SortButton 
              active={sortBy === 'monetary'} 
              onClick={() => setSortBy('monetary')}
              label="Spend"
            />
            <SortButton 
              active={sortBy === 'recency'} 
              onClick={() => setSortBy('recency')}
              label="Recent"
            />
          </div>
        </div>
      </div>

      {/* Customer List Header */}
      <div style={{ 
        padding: '8px 16px', 
        display: 'flex', 
        background: 'var(--bg-page)',
        fontSize: '11px',
        fontWeight: '600',
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.3px'
      }}>
        <div style={{ width: '60px' }}>ID</div>
        <div style={{ flex: 1 }}>Segment</div>
        <div style={{ width: '50px', textAlign: 'right' }}>Visits</div>
        <div style={{ width: '70px', textAlign: 'right' }}>Avg</div>
        <div style={{ width: '50px', textAlign: 'right' }}>Days</div>
      </div>

      {/* Customer List */}
      <div className="section">
        {loading ? (
          <div className="empty-state">
            <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
          </div>
        ) : regularCustomers.length === 0 ? (
          <div className="empty-state">
            <div style={{ color: 'var(--text-secondary)', fontWeight: '500', marginBottom: '4px' }}>
              No customers found
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              Load demo data from the Home tab
            </div>
          </div>
        ) : (
          regularCustomers.map((customer, i) => (
            <CustomerRow key={customer.customer_id} customer={customer} />
          ))
        )}
      </div>

      <div style={{ height: '16px' }} />
    </div>
  );
}

function SortButton({ active, onClick, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 12px',
        borderRadius: '6px',
        border: '1px solid',
        borderColor: active ? 'var(--accent)' : 'var(--divider)',
        background: active ? 'var(--accent-light)' : 'var(--bg-surface)',
        color: active ? 'var(--accent)' : 'var(--text-secondary)',
        fontSize: '12px',
        fontWeight: '500',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '4px'
      }}
    >
      {label}
      {active && <ChevronDown size={12} />}
    </button>
  );
}

function CustomerRow({ customer }) {
  const getSegmentStyle = (segment) => {
    switch (segment) {
      case 'champion':
        return { bg: 'var(--green-bg)', color: 'var(--green)' };
      case 'loyal':
        return { bg: 'var(--accent-light)', color: 'var(--accent)' };
      case 'at_risk':
        return { bg: 'var(--amber-bg)', color: 'var(--amber)' };
      case 'lost':
        return { bg: 'var(--red-bg)', color: 'var(--red)' };
      default:
        return { bg: '#F3F4F6', color: 'var(--text-secondary)' };
    }
  };

  const style = getSegmentStyle(customer.segment);

  return (
    <div className="list-row" style={{ padding: '10px 16px' }}>
      <div style={{ width: '60px', fontWeight: '500', fontSize: '13px' }}>
        {customer.label}
      </div>
      <div style={{ flex: 1 }}>
        <span 
          className="badge"
          style={{ background: style.bg, color: style.color }}
        >
          {customer.segment?.replace('_', ' ')}
        </span>
      </div>
      <div className="tabular-nums" style={{ width: '50px', textAlign: 'right', fontSize: '13px' }}>
        {customer.frequency}
      </div>
      <div className="tabular-nums" style={{ width: '70px', textAlign: 'right', fontSize: '13px' }}>
        ₹{customer.monetary_avg?.toFixed(0)}
      </div>
      <div className="tabular-nums" style={{ 
        width: '50px', 
        textAlign: 'right', 
        fontSize: '13px',
        color: customer.recency_days > 14 ? 'var(--amber)' : 'var(--text-secondary)'
      }}>
        {customer.recency_days}
      </div>
    </div>
  );
}
