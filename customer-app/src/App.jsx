import React, { useState, useEffect } from 'react';
import PhoneFrame from './components/PhoneFrame';
import Sidebar from './components/Sidebar';
import NotificationToast from './components/NotificationToast';
import HomePage from './pages/HomePage';
import OffersPage from './pages/OffersPage';
import QRScanner from './components/QRScanner';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function App() {
  const [activePage, setActivePage] = useState('home');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [offers, setOffers] = useState([]);
  const [notification, setNotification] = useState(null);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState(null);
  
  const customer = {
    id: 69,
    name: 'Rahul Sharma',
    phone: '+91 98765 43210',
    label: '#A69'
  };

  // Poll for offers
  useEffect(() => {
    const pollOffers = async () => {
      try {
        const response = await fetch(`${API_BASE}/customer/offers`);
        if (response.ok) {
          const data = await response.json();
          const customerOffers = (data.offers || []).filter(
            offer => offer.customer_id === customer.id
          );
          
          setOffers(prev => {
            if (customerOffers.length > prev.length && prev.length > 0) {
              const prevIds = new Set(prev.map(o => o.id));
              const newOffer = customerOffers.find(o => !prevIds.has(o.id));
              if (newOffer && !newOffer.redeemed) {
                setNotification({
                  title: `New offer from ${newOffer.merchant_name}`,
                  message: `Get ${newOffer.cashback_percent}% cashback on your next visit`,
                  offer: newOffer
                });
              }
            }
            return customerOffers;
          });
        }
      } catch (error) {
        // Silent fail
      }
    };

    pollOffers();
    const interval = setInterval(pollOffers, 3000);
    return () => clearInterval(interval);
  }, [customer.id]);

  const handleRedeem = (offer, redemptionDetails) => {
    setOffers(prev => prev.map(o => 
      o.id === offer.id 
        ? { ...o, redeemed: true, redemption_details: redemptionDetails } 
        : o
    ));
    setScannerOpen(false);
    setSelectedOffer(null);
    
    setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE}/customer/offers`);
        if (response.ok) {
          const data = await response.json();
          const customerOffers = (data.offers || []).filter(
            offer => offer.customer_id === customer.id
          );
          setOffers(customerOffers);
        }
      } catch (error) {
        // Silent fail
      }
    }, 500);
  };

  const handleScanQR = () => {
    // If there's an active offer, use it for scanning
    const activeOffer = offers.find(o => !o.redeemed);
    if (activeOffer) {
      setSelectedOffer(activeOffer);
    }
    setScannerOpen(true);
  };

  const renderPage = () => {
    switch (activePage) {
      case 'home':
        return (
          <HomePage 
            customer={customer}
            offers={offers}
            onMenuOpen={() => setSidebarOpen(true)}
            onViewOffers={() => setActivePage('offers')}
            onScanQR={handleScanQR}
          />
        );
      case 'offers':
        return (
          <OffersPage 
            offers={offers}
            customer={customer}
            onBack={() => setActivePage('home')}
            onRedeem={handleRedeem}
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
        Customer App · {customer.label}
      </div>
      
      <div style={{ position: 'relative' }}>
        <PhoneFrame>
          {renderPage()}
          
          <Sidebar 
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            customer={customer}
            offersCount={offers.filter(o => !o.redeemed).length}
            onNavigate={setActivePage}
            activePage={activePage}
          />
          
          {/* QR Scanner inside phone frame */}
          <QRScanner 
            isOpen={scannerOpen}
            onClose={() => {
              setScannerOpen(false);
              setSelectedOffer(null);
            }}
            offer={selectedOffer}
            onSuccess={handleRedeem}
          />
        </PhoneFrame>
        
        {notification && (
          <NotificationToast 
            notification={notification}
            onDismiss={() => setNotification(null)}
            onClick={() => {
              setNotification(null);
              setActivePage('offers');
            }}
          />
        )}
      </div>
    </div>
  );
}
