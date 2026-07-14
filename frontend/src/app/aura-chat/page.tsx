"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function AuraChat() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello. I'm Aura, your secure space for reflection. How has your week been?", isAura: true },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedUserId = localStorage.getItem("user_id");
    if (!savedUserId) {
      alert("Please log in first to chat with Aura.");
      router.push("/");
      return;
    }
    setUserId(savedUserId);
  }, [router]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || !userId) return;
    
    const newUserMsg = { id: Date.now(), text: input, isAura: false };
    setMessages(prev => [...prev, newUserMsg]);
    const liveInput = input;
    setInput("");
    setIsTyping(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/aura/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, message: liveInput }),
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: data.response,
          isAura: true
        }]);
      } else {
        const errData = await res.json();
        console.error("Error from Aura chat API:", errData);
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: "I'm sorry, I'm having trouble connecting to my memory right now. Please try again in a moment.",
          isAura: true
        }]);
      }
    } catch (err) {
      console.error("Failed to connect to Aura server:", err);
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: "I couldn't reach the server. Please ensure the backend is running.",
        isAura: true
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="h-[100dvh] overflow-hidden bg-[var(--background)] flex flex-col items-center pt-6 pb-8 px-4 sm:px-8">
      
      {/* Header */}
      <div className="w-full flex items-center justify-between mb-6">
        <Link 
          href="/dashboard" 
          className="flex items-center gap-2 text-sm font-bold text-[var(--foreground)] neu-raised px-4 py-2 rounded-full transition-all duration-300 active:neu-pressed"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-4 h-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Dashboard
        </Link>
        
        <div className="flex flex-col items-center">
          <h1 className="text-3xl font-extrabold text-[var(--foreground)]">
            Aura
          </h1>
          <p className="text-[10px] text-[var(--foreground)] uppercase tracking-[0.2em] mt-0.5 font-bold opacity-70">
            Secure Space
          </p>
        </div>
        
        {/* Memory Active Indicator */}
        <div className="flex items-center gap-2 neu-pressed px-4 py-2 rounded-full">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
          <span className="text-xs font-bold text-[var(--foreground)]/70 tracking-wide">Memory Active</span>
        </div>
      </div>

      {/* Chat Window */}
      <div className="w-full flex-1 neu-surface flex flex-col overflow-hidden">
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-8 flex flex-col gap-6 custom-scrollbar">
          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 items-end ${msg.isAura ? 'flex-row' : 'flex-row-reverse'}`}>
              
              {/* Avatar */}
              <div className={`w-9 h-9 flex-shrink-0 rounded-full flex items-center justify-center neu-raised text-[var(--foreground)]`}>
                {msg.isAura ? (
                  <svg className="w-5 h-5 text-[var(--foreground)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-[var(--foreground)]/60" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                )}
              </div>

              {/* Message Bubble */}
              <div 
                className={`max-w-[80%] sm:max-w-[70%] px-5 py-3.5 text-[15px] leading-relaxed transition-all duration-300 animate-in fade-in slide-in-from-bottom-2 font-medium ${
                  msg.isAura 
                  ? 'neu-raised text-[var(--foreground)] rounded-2xl rounded-bl-sm' 
                  : 'neu-pressed bg-[var(--primary-accent)]/30 text-[var(--foreground)] rounded-2xl rounded-br-sm'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex gap-3 items-end">
              <div className="w-9 h-9 flex-shrink-0 rounded-full flex items-center justify-center neu-raised text-[var(--foreground)]">
                <svg className="w-5 h-5 text-[var(--foreground)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
                </svg>
              </div>
              <div className="neu-raised px-5 py-4 rounded-2xl rounded-bl-sm flex gap-1.5 items-center">
                <span className="w-1.5 h-1.5 bg-[var(--foreground)]/40 rounded-full animate-bounce"></span>
                <span className="w-1.5 h-1.5 bg-[var(--foreground)]/40 rounded-full animate-bounce" style={{animationDelay: '0.15s'}}></span>
                <span className="w-1.5 h-1.5 bg-[var(--foreground)]/40 rounded-full animate-bounce" style={{animationDelay: '0.3s'}}></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 sm:p-5 border-t border-[var(--foreground)]/5">
          <div className="flex items-center gap-3 neu-pressed p-2 sm:p-2.5 rounded-full transition-all duration-300 focus-within:ring-2 focus-within:ring-[var(--primary-accent)]/50">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type your thoughts..."
              className="flex-1 bg-transparent border-none outline-none px-4 py-1 text-[var(--foreground)] placeholder:text-[var(--foreground)]/40 font-medium"
            />
            <button 
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className="neu-raised text-[var(--foreground)] p-3 rounded-full transition-all duration-300 disabled:opacity-50 active:neu-pressed"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
