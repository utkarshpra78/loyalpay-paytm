import React from 'react';
import { ArrowLeft, TrendingUp, TrendingDown, Clock, Calendar, Users } from 'lucide-react';

export default function InsightsPage({ insights, customerHabits, onBack, loading }) {
  return (
    <div className="min-h-full">
      {/* Header */}
      <div className="section">
        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <ArrowLeft size={20} style={{ color: 'var(--text-primary)' }} />
          </button>
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>Business Trends</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Based on last 60 days
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
        </div>
      ) : !insights || insights.length === 0 ? (
        <div className="empty-state">
          <div style={{ color: 'var(--text-secondary)', fontWeight: '500', marginBottom: '4px' }}>
            No insights yet
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
            Load demo data to see business trends
          </div>
        </div>
      ) : (
        <>
          {/* Key Insights */}
          <div className="section">
            <div className="section-header">
              <span className="section-title">Key Findings</span>
            </div>
            
            {insights.map((insight, i) => (
              <div key={i} className="list-row">
                <div className="icon-box" style={{ 
                  background: insight.type === 'positive' ? 'var(--green-bg)' : 
                              insight.type === 'warning' ? 'var(--amber-bg)' : '#F3F4F6'
                }}>
                  {insight.type === 'positive' ? (
                    <TrendingUp size={18} style={{ color: 'var(--green)' }} />
                  ) : insight.type === 'warning' ? (
                    <TrendingDown size={18} style={{ color: 'var(--amber)' }} />
                  ) : (
                    <TrendingUp size={18} style={{ color: 'var(--text-secondary)' }} />
                  )}
                </div>
                <div style={{ flex: 1, marginLeft: '12px' }}>
                  <div style={{ fontWeight: '500', marginBottom: '2px' }}>{insight.title}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                    {insight.description}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="spacer" />

          {/* Customer Habits */}
          {customerHabits && customerHabits.length > 0 && (
            <div className="section">
              <div className="section-header">
                <span className="section-title">Customer Habits</span>
              </div>
              
              {customerHabits.slice(0, 8).map((habit, i) => (
                <div key={i} className="list-row" style={{ padding: '10px 16px' }}>
                  <div style={{ width: '50px', fontWeight: '500', fontSize: '13px' }}>
                    {habit.label}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {habit.preferred_day && (
                        <span style={{ 
                          fontSize: '11px', 
                          color: 'var(--text-secondary)',
                          background: '#F3F4F6',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          <Calendar size={10} style={{ display: 'inline', marginRight: '4px' }} />
                          {habit.preferred_day}
                        </span>
                      )}
                      {habit.preferred_time && (
                        <span style={{ 
                          fontSize: '11px', 
                          color: 'var(--text-secondary)',
                          background: '#F3F4F6',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          <Clock size={10} style={{ display: 'inline', marginRight: '4px' }} />
                          {habit.preferred_time}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="tabular-nums" style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    {habit.visit_count} visits
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <div style={{ height: '16px' }} />
    </div>
  );
}
