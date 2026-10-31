import React from 'react';
import { ChevronRight, AlertTriangle, Users, IndianRupee, Calendar, ArrowUpRight } from 'lucide-react';

export default function HomePage({ summary, segments, insights, atRiskCustomers, onNavigate, loading }) {
  const formatCurrency = (amount) => {
    if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(1)}L`;
    }
    return `₹${(amount || 0).toLocaleString('en-IN')}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  };

  const atRiskCount = atRiskCustomers?.length || 0;

  return (
    <div className="min-h-full">
      {/* Header */}
      <div className="section" style={{ background: 'var(--accent)' }}>
        <div style={{ padding: '16px' }}>
          {/* Paytm for Merchant */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ 
              fontWeight: '800', 
              fontSize: '18px', 
              color: 'white',
              fontFamily: 'Arial, sans-serif',
              letterSpacing: '-0.3px'
            }}>
              Paytm
            </span>
            <span style={{ 
              color: 'rgba(255,255,255,0.8)', 
              fontSize: '14px'
            }}>
              for Merchant
            </span>
          </div>
          <div style={{ color: 'white', fontSize: '18px', fontWeight: '600' }}>
            Ramesh Kirana Store
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="section">
        <div style={{ padding: '16px', display: 'flex', gap: '12px' }}>
          {/* Total Revenue */}
          <div style={{ flex: 1 }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '4px' }}>
              Total Revenue
            </div>
            <div className="amount-lg tabular-nums">
              {formatCurrency(summary?.total_revenue)}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '2px' }}>
              Last 60 days
            </div>
          </div>
          
          {/* Divider */}
          <div style={{ width: '1px', background: 'var(--divider)' }} />
          
          {/* Transactions */}
          <div style={{ flex: 1 }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '4px' }}>
              Transactions
            </div>
            <div className="amount-lg tabular-nums">
              {(summary?.total_transactions || 0).toLocaleString('en-IN')}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '2px' }}>
              ₹{summary?.avg_transaction?.toFixed(0) || 0} avg
            </div>
          </div>
        </div>
      </div>

      <div className="spacer" />

      {/* Customer Overview */}
      <div className="section">
        <div className="section-header">
          <span className="section-title">Customer Overview</span>
        </div>
        
        {/* Regular Customers */}
        <button 
          className="list-row"
          onClick={() => onNavigate('regulars')}
          style={{ cursor: 'pointer', width: '100%', textAlign: 'left' }}
        >
          <div className="icon-box" style={{ background: 'var(--accent-light)' }}>
            <Users size={18} style={{ color: 'var(--accent)' }} />
          </div>
          <div style={{ flex: 1, marginLeft: '12px' }}>
            <div style={{ fontWeight: '500' }}>Regular Customers</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              Visited 2+ times in last 60 days
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="amount tabular-nums" style={{ fontSize: '18px' }}>
              {summary?.regular_customers || 0}
            </span>
            <ChevronRight size={18} style={{ color: 'var(--text-muted)' }} />
          </div>
        </button>

        {/* At-Risk (includes Lost) */}
        <button 
          className="list-row"
          onClick={() => onNavigate('offers')}
          style={{ cursor: 'pointer', width: '100%', textAlign: 'left' }}
        >
          <div className="icon-box" style={{ background: 'var(--amber-bg)' }}>
            <AlertTriangle size={18} style={{ color: 'var(--amber)' }} />
          </div>
          <div style={{ flex: 1, marginLeft: '12px' }}>
            <div style={{ fontWeight: '500' }}>At-Risk & Lost</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              Haven't visited in 14+ days
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="amount tabular-nums" style={{ fontSize: '18px', color: 'var(--amber)' }}>
              {atRiskCount}
            </span>
            <ChevronRight size={18} style={{ color: 'var(--text-muted)' }} />
          </div>
        </button>
      </div>

      <div className="spacer" />

      {/* Quick Actions */}
      <div className="section">
        <div className="section-header">
          <span className="section-title">Quick Actions</span>
        </div>
        
        <button 
          className="list-row"
          onClick={() => onNavigate('offers')}
          style={{ cursor: 'pointer', width: '100%', textAlign: 'left' }}
        >
          <div className="icon-box" style={{ background: 'var(--green-bg)' }}>
            <IndianRupee size={18} style={{ color: 'var(--green)' }} />
          </div>
          <div style={{ flex: 1, marginLeft: '12px' }}>
            <div style={{ fontWeight: '500' }}>Send Cashback Offer</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              Bring back {atRiskCount} customers
            </div>
          </div>
          <ChevronRight size={18} style={{ color: 'var(--text-muted)' }} />
        </button>

        <button 
          className="list-row"
          onClick={() => onNavigate('chat')}
          style={{ cursor: 'pointer', width: '100%', textAlign: 'left' }}
        >
          <div className="icon-box" style={{ background: '#F3E8FF' }}>
            <ArrowUpRight size={18} style={{ color: '#7C3AED' }} />
          </div>
          <div style={{ flex: 1, marginLeft: '12px' }}>
            <div style={{ fontWeight: '500' }}>Ask AI for advice</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              Get personalised suggestions
            </div>
          </div>
          <ChevronRight size={18} style={{ color: 'var(--text-muted)' }} />
        </button>
      </div>

      <div className="spacer" />

      {/* Recent Insights */}
      {insights && insights.length > 0 && (
        <div className="section">
          <div className="section-header">
            <span className="section-title">Recent Insights</span>
            <button 
              className="section-link"
              onClick={() => onNavigate('insights')}
            >
              View all
            </button>
          </div>
          
          {insights.slice(0, 3).map((insight, i) => (
            <div key={i} className="list-row">
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: '500', marginBottom: '2px' }}>{insight.title}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                  {insight.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Segment Breakdown */}
      <div className="section">
        <div className="section-header">
          <span className="section-title">Customer Segments</span>
        </div>
        
        <div style={{ padding: '12px 16px' }}>
          <SegmentRow 
            label="Champion" 
            count={segments?.Champion || 0} 
            total={summary?.total_customers || 1}
            color="var(--green)"
          />
          <SegmentRow 
            label="Loyal" 
            count={segments?.Loyal || 0} 
            total={summary?.total_customers || 1}
            color="var(--accent)"
          />
          <SegmentRow 
            label="Recent" 
            count={(segments?.New || 0) + (segments?.Casual || 0)} 
            total={summary?.total_customers || 1}
            color="#6B7280"
          />
          <SegmentRow 
            label="At-Risk" 
            count={segments?.['At-Risk'] || 0} 
            total={summary?.total_customers || 1}
            color="var(--amber)"
          />
          <SegmentRow 
            label="Lost" 
            count={segments?.Lost || 0} 
            total={summary?.total_customers || 1}
            color="var(--red)"
            isLast
          />
        </div>
      </div>

      {/* Bottom padding */}
      <div style={{ height: '16px' }} />
    </div>
  );
}

function SegmentRow({ label, count, total, color, isLast }) {
  const percentage = total > 0 ? (count / total) * 100 : 0;
  
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '12px',
      paddingBottom: isLast ? 0 : '12px',
      marginBottom: isLast ? 0 : '12px',
      borderBottom: isLast ? 'none' : '1px solid var(--divider)'
    }}>
      <div style={{ width: '70px', fontSize: '13px', color: 'var(--text-secondary)' }}>
        {label}
      </div>
      <div style={{ flex: 1 }}>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ 
              width: `${Math.max(percentage, 2)}%`,
              background: color 
            }} 
          />
        </div>
      </div>
      <div className="tabular-nums" style={{ 
        width: '36px', 
        textAlign: 'right', 
        fontWeight: '500',
        fontSize: '13px'
      }}>
        {count}
      </div>
    </div>
  );
}
