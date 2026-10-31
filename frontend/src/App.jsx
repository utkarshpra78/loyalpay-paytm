import React, { useState, useEffect, useCallback } from 'react';
import PhoneFrame from './components/PhoneFrame';
import BottomNav from './components/BottomNav';
import HomePage from './pages/HomePage';
import RegularsPage from './pages/RegularsPage';
import InsightsPage from './pages/InsightsPage';
import OffersPage from './pages/OffersPage';
import ChatPage from './pages/ChatPage';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [loading, setLoading] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);
  
  // Data state
  const [summary, setSummary] = useState(null);
  const [segments, setSegments] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [atRiskCustomers, setAtRiskCustomers] = useState([]);
  const [lostCustomers, setLostCustomers] = useState([]);
  const [insights, setInsights] = useState([]);
  const [customerHabits, setCustomerHabits] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);

  // Fetch all data
  const fetchData = useCallback(async () => {
    try {
      const [summaryRes, segmentsRes, customersRes, atRiskRes, lostRes, insightsRes] = await Promise.all([
        fetch(`${API_BASE}/store-summary`),
        fetch(`${API_BASE}/segments`),
        fetch(`${API_BASE}/customers?limit=200`),
        fetch(`${API_BASE}/at-risk`),
        fetch(`${API_BASE}/lost`),
        fetch(`${API_BASE}/insights`),
      ]);

      if (summaryRes.ok) setSummary(await summaryRes.json());
      if (segmentsRes.ok) setSegments(await segmentsRes.json());
      if (customersRes.ok) {
        const data = await customersRes.json();
        setCustomers(data.customers || []);
      }
      if (atRiskRes.ok) {
        const data = await atRiskRes.json();
        setAtRiskCustomers(data.customers || []);
      }
      if (lostRes.ok) {
        const data = await lostRes.json();
        setLostCustomers(data.customers || []);
      }
      if (insightsRes.ok) {
        const data = await insightsRes.json();
        setInsights(data.insights || []);
        setCustomerHabits(data.customer_habits || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  }, []);

  // Auto-load demo data on mount
  useEffect(() => {
    const loadDemoData = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${API_BASE}/simulate/fast-forward`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ days: 60 }),
        });
        
        if (response.ok) {
          setDataLoaded(true);
          await fetchData();
        }
      } catch (error) {
        console.error('Error loading demo data:', error);
      }
      setLoading(false);
    };

    loadDemoData();
  }, [fetchData]);

  // Poll for updates every 5 seconds (to see redemptions reflected)
  useEffect(() => {
    if (!dataLoaded) return;
    
    const interval = setInterval(() => {
      fetchData();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [dataLoaded, fetchData]);

  // Create campaign
  const handleCreateCampaign = async (cashbackPercent, customerIds) => {
    try {
      const response = await fetch(`${API_BASE}/create-campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cashback_percent: cashbackPercent,
          customer_ids: customerIds,
          budget: 1000,
        }),
      });
      
      if (response.ok) {
        await fetchData();
        return true;
      }
    } catch (error) {
      console.error('Error creating campaign:', error);
    }
    return false;
  };

  const handleNavigate = (tab) => {
    setActiveTab(tab);
  };

  const renderPage = () => {
    switch (activeTab) {
      case 'home':
        return (
          <HomePage
            summary={summary}
            segments={segments}
            insights={insights}
            atRiskCustomers={atRiskCustomers}
            onNavigate={handleNavigate}
            loading={loading}
          />
        );
      case 'regulars':
        return (
          <RegularsPage
            customers={customers}
            onBack={() => setActiveTab('home')}
            loading={loading}
          />
        );
      case 'insights':
        return (
          <InsightsPage
            insights={insights}
            customerHabits={customerHabits}
            onBack={() => setActiveTab('home')}
            loading={loading}
          />
        );
      case 'offers':
        return (
          <OffersPage
            atRiskCustomers={atRiskCustomers}
            onCreateCampaign={handleCreateCampaign}
            onBack={() => setActiveTab('home')}
            loading={loading}
          />
        );
      case 'chat':
        return (
          <ChatPage
            messages={chatMessages}
            setMessages={setChatMessages}
            onBack={() => setActiveTab('home')}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#E5E7EB', 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center', 
      justifyContent: 'center',
      padding: '32px'
    }}>
      {/* App label - Above the phone */}
      <div style={{ 
        background: 'white',
        padding: '8px 20px',
        borderRadius: '20px',
        fontSize: '13px',
        fontWeight: '500',
        color: '#5F6368',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        marginBottom: '16px'
      }}>
        Merchant App
      </div>
      
      <PhoneFrame>
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {renderPage()}
          </div>
          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </PhoneFrame>
    </div>
  );
}
