import React, { useState, useEffect, useRef } from 'react';
import MaintenanceView from './components/MaintenanceView';

export const MAINTENANCE_LOCKDOWN = false;
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';
import AuthModal from './components/AuthModal';
import PricingModal from './components/PricingModal';
import Toast from './components/Toast';
import { 
  subscribeAuthState, 
  logoutUser 
} from './services/firebase';
import {
  fetchSubscriptionStatus,
  fetchConversations,
  fetchConversationMessages,
  createConversation,
  renameConversation,
  deleteConversation,
  streamChat,
} from './services/api';

export default function App() {
  if (MAINTENANCE_LOCKDOWN) {
    return <MaintenanceView />;
  }
  // Application State
  const [currentUser, setCurrentUser] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  
  // UI Controls (Sidebar open by default on desktop, closed on mobile)
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [pricingModalOpen, setPricingModalOpen] = useState(false);
  const [toast, setToast] = useState(null);

  // Progressive Web App (PWA) / Android Install State
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isInstallable, setIsInstallable] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  const abortControllerRef = useRef(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // PWA Install Prompt & Standalone Mode Detection
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkStandalone = 
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true ||
      document.referrer.includes('android-app://');
    setIsStandalone(Boolean(checkStandalone));

    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setIsInstallable(true);
    };

    const handleAppInstalled = () => {
      setIsInstallable(false);
      setDeferredPrompt(null);
      setIsStandalone(true);
      showToast('🎉 FRIDAY AI successfully installed to your home screen!', 'success');
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstallApp = async () => {
    if (deferredPrompt) {
      try {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') {
          setIsInstallable(false);
          setDeferredPrompt(null);
        }
      } catch (err) {
        console.warn('PWA install prompt error:', err);
      }
    } else {
      showToast('Tap browser menu (⋮) -> "Install app" or "Add to Home screen"', 'info');
    }
  };

  // 1. Subscribe to Firebase Auth
  useEffect(() => {
    const unsubscribe = subscribeAuthState((user) => {
      setCurrentUser(user);
      loadSubscription();
      loadConversations();
    });
    return () => unsubscribe();
  }, []);

  const loadSubscription = async () => {
    try {
      const data = await fetchSubscriptionStatus();
      if (data) setSubscription(data);
    } catch (err) {
      console.warn('Subscription fetch warning:', err);
    }
  };

  const loadConversations = async () => {
    try {
      const convs = await fetchConversations();
      if (Array.isArray(convs) && convs.length > 0) {
        setConversations(convs);
        localStorage.setItem('friday_cached_convs', JSON.stringify(convs));
      } else {
        const cached = localStorage.getItem('friday_cached_convs');
        if (cached) {
          try { setConversations(JSON.parse(cached)); } catch (_) {}
        }
      }
    } catch (err) {
      const cached = localStorage.getItem('friday_cached_convs');
      if (cached) {
        try { setConversations(JSON.parse(cached)); } catch (_) {}
      }
    }
  };

  // 2. Select / Load Conversation (Instant <1ms response + background sync)
  const handleSelectConversation = async (convId) => {
    if (convId === activeConvId) return;
    setActiveConvId(convId);
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }

    // 1. Instant local cache retrieval (<1ms)
    let loadedFromCache = false;
    const localCached = localStorage.getItem(`friday_conv_msgs_${convId}`);
    if (localCached) {
      try {
        const parsed = JSON.parse(localCached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          loadedFromCache = true;
        }
      } catch (_) {}
    }

    // 2. Background sync from server (if authenticated)
    try {
      const data = await fetchConversationMessages(convId);
      if (data && Array.isArray(data.messages)) {
        setMessages(data.messages);
        localStorage.setItem(`friday_conv_msgs_${convId}`, JSON.stringify(data.messages));
      }
    } catch (err) {
      if (!loadedFromCache) {
        console.warn('Could not load remote mission logs:', err);
      }
    }
  };

  // 3. Start New Operation
  const handleNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setInput('');
    setCurrentStreamText('');
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  // 4. Delete Conversation
  const handleDeleteConversation = async (convId) => {
    localStorage.removeItem(`friday_conv_msgs_${convId}`);
    try {
      await deleteConversation(convId);
      setConversations((prev) => {
        const updated = prev.filter((c) => c.id !== convId);
        localStorage.setItem('friday_cached_convs', JSON.stringify(updated));
        return updated;
      });
      if (activeConvId === convId) {
        handleNewChat();
      }
      showToast('Operation record purged', 'success');
    } catch (err) {
      setConversations((prev) => {
        const updated = prev.filter((c) => c.id !== convId);
        localStorage.setItem('friday_cached_convs', JSON.stringify(updated));
        return updated;
      });
      if (activeConvId === convId) {
        handleNewChat();
      }
      showToast('Operation removed', 'info');
    }
  };

  // 5. Rename Conversation
  const handleRenameConversation = async (convId, title) => {
    try {
      await renameConversation(convId, title);
      setConversations((prev) => {
        const updated = prev.map((c) => (c.id === convId ? { ...c, title } : c));
        localStorage.setItem('friday_cached_convs', JSON.stringify(updated));
        return updated;
      });
      showToast('Operation retitled', 'success');
    } catch (err) {
      setConversations((prev) => {
        const updated = prev.map((c) => (c.id === convId ? { ...c, title } : c));
        localStorage.setItem('friday_cached_convs', JSON.stringify(updated));
        return updated;
      });
      showToast('Operation title updated locally', 'info');
    }
  };

  // 6. Send Message / Transmit Directive
  const handleSendMessage = async (customPrompt) => {
    const textToSend = (customPrompt || input).trim();
    if (!textToSend || isStreaming) return;

    setInput('');
    let convId = activeConvId;

    // Create conversation on backend if not existing
    if (!convId) {
      convId = 'conv_' + Math.random().toString(36).substring(2, 12);
      const derivedTitle = textToSend.slice(0, 32) + (textToSend.length > 32 ? '…' : '');
      setActiveConvId(convId);
      try {
        await createConversation(convId, derivedTitle);
        setConversations((prev) => {
          const updated = [{ id: convId, title: derivedTitle }, ...prev];
          localStorage.setItem('friday_cached_convs', JSON.stringify(updated));
          return updated;
        });
      } catch (_) {
        setConversations((prev) => {
          const updated = [{ id: convId, title: derivedTitle }, ...prev];
          localStorage.setItem('friday_cached_convs', JSON.stringify(updated));
          return updated;
        });
      }
    }

    const updatedMessages = [...messages, { role: 'user', content: textToSend }];
    setMessages(updatedMessages);
    localStorage.setItem(`friday_conv_msgs_${convId}`, JSON.stringify(updatedMessages));

    // Optimistically update quota pill
    if (subscription && !subscription.is_unlimited && subscription.chats_remaining !== null) {
      setSubscription((prev) => ({
        ...prev,
        chats_remaining: Math.max(0, (prev?.chats_remaining ?? 5) - 1),
      }));
    }

    setIsStreaming(true);
    setCurrentStreamText('');
    abortControllerRef.current = new AbortController();

    let fullStreamText = '';

    await streamChat({
      messages: updatedMessages,
      conversationId: convId,
      model: 'cognitivecomputations/dolphin-mistral-24b-venice-edition',
      signal: abortControllerRef.current.signal,
      onChunk: (chunk) => {
        fullStreamText += chunk;
        setCurrentStreamText(fullStreamText);
      },
      onDone: () => {
        setIsStreaming(false);
        if (fullStreamText.trim()) {
          const finalMessages = [...updatedMessages, { role: 'assistant', content: fullStreamText }];
          setMessages(finalMessages);
          localStorage.setItem(`friday_conv_msgs_${convId}`, JSON.stringify(finalMessages));
        }
        setCurrentStreamText('');
        loadSubscription();
        loadConversations();
      },
      onError: (err) => {
        setIsStreaming(false);
        setCurrentStreamText('');

        if (err.status === 401) {
          setAuthModalOpen(true);
          showToast('Session required. Please sign in to transmit directives.', 'error');
        } else if (err.status === 429 || err.status === 403) {
          setPricingModalOpen(true);
          showToast('Daily chat limit reached. Upgrade to Cyber Pro for unlimited access!', 'error');
        } else {
          // Guaranteed fallback: display clear error rather than an empty bubble
          setMessages((prev) => [
            ...prev,
            { 
              role: 'assistant', 
              content: `⚠️ **Inference Transmission Alert**: ${err.message || 'Server temporarily unreachable. Please retry.'}` 
            }
          ]);
          showToast(err.message || 'Stream generation failed', 'error');
        }
      },
    });
  };

  // 7. Halt / Stop Streaming
  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsStreaming(false);
    if (currentStreamText.trim()) {
      setMessages((prev) => [...prev, { role: 'assistant', content: currentStreamText }]);
    }
    setCurrentStreamText('');
    showToast('Generation halted by operator', 'info');
  };

  // 8. Regenerate last response
  const handleRegenerate = () => {
    if (messages.length === 0 || isStreaming) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      // Remove last assistant message
      setMessages((prev) => {
        const copy = [...prev];
        if (copy[copy.length - 1]?.role === 'assistant') {
          copy.pop();
        }
        return copy;
      });
      handleSendMessage(lastUserMsg.content);
    }
  };

  return (
    <div className="flex h-[100dvh] max-h-[100dvh] w-screen overflow-hidden bg-[#070709] text-[#F5F5F5] font-sans stealth-glow">
      {/* Sidebar Navigation */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations}
        activeConvId={activeConvId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        currentUser={currentUser}
        subscription={subscription}
        onOpenAuth={() => setAuthModalOpen(true)}
        onOpenPricing={() => setPricingModalOpen(true)}
        onInstallApp={handleInstallApp}
        isInstallable={isInstallable}
        isStandalone={isStandalone}
        onLogout={async () => {
          await logoutUser();
          setCurrentUser(null);
          handleNewChat();
          showToast('Operator session disconnected', 'info');
        }}
      />

      {/* Main Execution Arena */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-[#070709]">
        <Header
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          subscription={subscription}
          onOpenPricing={() => setPricingModalOpen(true)}
          modelName="friday Cyber Cloud"
          onInstallApp={handleInstallApp}
          isInstallable={isInstallable}
          isStandalone={isStandalone}
        />

        <ChatArea
          messages={messages}
          isStreaming={isStreaming}
          currentStreamText={currentStreamText}
          onSelectPrompt={(prompt) => handleSendMessage(prompt)}
          onRegenerate={handleRegenerate}
        />

        <ChatInput
          input={input}
          setInput={setInput}
          onSendMessage={() => handleSendMessage()}
          onStopStreaming={handleStopStreaming}
          isStreaming={isStreaming}
          disabled={isStreaming}
        />
      </div>

      {/* Modals & Overlays */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={() => {
          loadSubscription();
          loadConversations();
          showToast('Authentication validated. Access granted.', 'success');
        }}
      />

      <PricingModal
        isOpen={pricingModalOpen}
        onClose={() => setPricingModalOpen(false)}
        currentUser={currentUser}
        onOpenAuth={() => setAuthModalOpen(true)}
        onPaymentSuccess={() => {
          loadSubscription();
          showToast('🎉 Friday Cyber Pro Activated! Unlimited compute granted.', 'success');
        }}
      />

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
