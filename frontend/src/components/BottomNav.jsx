import React from 'react';
import { Home, Users, TrendingUp, Gift, MessageCircle } from 'lucide-react';

const tabs = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'regulars', label: 'Regulars', icon: Users },
  { id: 'insights', label: 'Trends', icon: TrendingUp },
  { id: 'offers', label: 'Offers', icon: Gift },
  { id: 'chat', label: 'Ask AI', icon: MessageCircle },
];

export default function BottomNav({ activeTab, onTabChange }) {
  return (
    <nav className="bottom-nav">
      {tabs.map(tab => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
