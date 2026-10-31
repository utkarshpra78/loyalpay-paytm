import React from 'react';
import { Signal, Wifi, Battery } from 'lucide-react';

export default function PhoneFrame({ children }) {
  const now = new Date();
  const time = now.toLocaleTimeString('en-IN', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  });

  return (
    <div className="phone-frame">
      {/* Android Status Bar */}
      <div className="status-bar">
        <span>{time}</span>
        <div className="status-bar-icons">
          <Signal size={14} strokeWidth={2} />
          <Wifi size={14} strokeWidth={2} />
          <Battery size={14} strokeWidth={2} />
        </div>
      </div>
      
      {/* Content */}
      <div className="phone-content">
        {children}
      </div>
    </div>
  );
}
