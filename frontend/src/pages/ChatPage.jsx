import React, { useState, useRef, useEffect } from 'react';
import { ArrowLeft, Send, User } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function ChatPage({ messages, setMessages, onBack }) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      } else {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: 'Sorry, I encountered an error. Please try again.' 
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Connection error. Please check your internet.' 
      }]);
    }

    setIsLoading(false);
  };

  const suggestions = [
    "How many at-risk customers do I have?",
    "Who are my top 5 customers?",
    "Which customers spend above ₹50?",
    "What's my revenue this month?"
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div className="section" style={{ flexShrink: 0 }}>
        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            <ArrowLeft size={20} style={{ color: 'var(--text-primary)' }} />
          </button>
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>Ask AI</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Ask about your customers & business
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {messages.length === 0 ? (
          <div>
            <div style={{ 
              color: 'var(--text-secondary)', 
              fontSize: '13px', 
              marginBottom: '16px',
              textAlign: 'center'
            }}>
              Try asking:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {suggestions.map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => setInput(suggestion)}
                  style={{
                    padding: '12px',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--divider)',
                    borderRadius: '8px',
                    textAlign: 'left',
                    fontSize: '13px',
                    color: 'var(--text-primary)',
                    cursor: 'pointer'
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '10px 14px',
                    borderRadius: '12px',
                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-surface)',
                    color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                    fontSize: '14px',
                    lineHeight: '1.5',
                    border: msg.role === 'assistant' ? '1px solid var(--divider)' : 'none'
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div style={{
                  padding: '10px 14px',
                  borderRadius: '12px',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--divider)',
                  color: 'var(--text-muted)',
                  fontSize: '14px'
                }}>
                  Thinking...
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ 
        padding: '12px 16px', 
        background: 'var(--bg-surface)', 
        borderTop: '1px solid var(--divider)',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask a question..."
            className="input"
            style={{ flex: 1 }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '8px',
              border: 'none',
              background: input.trim() ? 'var(--accent)' : 'var(--divider)',
              color: 'white',
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
