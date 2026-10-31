import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2, Edit2, Search, X, ShieldAlert, User, LogOut, Sparkles } from 'lucide-react';

export default function Sidebar({
  isOpen,
  onClose,
  conversations = [],
  activeConvId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onRenameConversation,
  currentUser,
  subscription,
  onOpenAuth,
  onOpenPricing,
  onLogout,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const filtered = conversations.filter(c => 
    (c.title || 'New Operation').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleStartRename = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title || 'New Operation');
  };

  const handleSaveRename = (e, convId) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRenameConversation(convId, editTitle.trim());
    }
    setEditingId(null);
  };

  const isPro = subscription?.is_unlimited;

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          onClick={onClose}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 md:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside className={`
        fixed md:static inset-y-0 left-0 z-40
        w-72 bg-[#09090c] border-r border-[#1c1c22] flex flex-col justify-between
        transform transition-transform duration-200 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Top Header */}
        <div className="p-3.5 flex flex-col gap-3 border-b border-[#18181f]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#121217] border border-[#FF3038]/50 flex items-center justify-center shadow-[0_0_10px_rgba(255,48,56,0.25)]">
                <span className="font-heading font-black text-xs text-[#FF3038]">F</span>
              </div>
              <div className="flex flex-col">
                <span className="font-heading font-bold text-sm tracking-wide text-zinc-100">FRIDAY AI</span>
                <span className="text-[10px] font-mono text-zinc-500">v2.0 Cyber Red Team</span>
              </div>
            </div>

            <button 
              onClick={onClose}
              className="p-1 rounded-lg text-zinc-500 hover:text-white md:hidden"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* New Chat Button */}
          <button
            onClick={onNewChat}
            className="w-full py-2.5 px-3 rounded-xl bg-[#121217] hover:bg-[#1a1a22] border border-[#262633] hover:border-[#FF3038]/50 text-xs font-mono font-semibold text-zinc-200 hover:text-white flex items-center justify-center gap-2 transition-all shadow-sm active:scale-98"
          >
            <Plus className="w-4 h-4 text-[#FF3038]" />
            <span>New Operation</span>
          </button>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search missions…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#101014] border border-[#1e1e26] rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-[#FF3038]/60 font-mono transition-colors"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
          <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">
            Active Targets
          </div>

          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs font-mono text-zinc-600">
              No operations logged
            </div>
          ) : (
            filtered.map((conv) => {
              const isActive = conv.id === activeConvId;
              const isEditing = editingId === conv.id;

              return (
                <div
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={`
                    group relative flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-xs transition-colors
                    ${isActive 
                      ? 'bg-[#15151c] text-white font-medium border-l-2 border-[#FF3038]' 
                      : 'text-zinc-400 hover:bg-[#111116] hover:text-zinc-200'}
                  `}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1 mr-1">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-[#FF3038]' : 'text-zinc-500'}`} />
                    {isEditing ? (
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={(e) => handleSaveRename(e, conv.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(e, conv.id);
                          if (e.key === 'Escape') setEditingId(null);
                        }}
                        autoFocus
                        className="bg-[#1c1c24] border border-[#FF3038]/50 rounded px-1.5 py-0.5 text-xs text-white w-full outline-none"
                      />
                    ) : (
                      <span className="truncate font-sans">{conv.title || 'New Operation'}</span>
                    )}
                  </div>

                  {/* Actions */}
                  {!isEditing && (
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
                      <button
                        onClick={(e) => handleStartRename(e, conv)}
                        className="p-1 rounded text-zinc-500 hover:text-zinc-200"
                        title="Rename"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(conv.id);
                        }}
                        className="p-1 rounded text-zinc-500 hover:text-[#FF3038]"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Bottom Profile / Account Pill */}
        <div className="p-3 border-t border-[#18181f] bg-[#0b0b0e]">
          {currentUser ? (
            <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-[#121217] border border-[#1e1e24]">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-full bg-[#1e1e26] border border-[#FF3038]/40 flex items-center justify-center font-heading font-bold text-xs text-[#FF3038] shrink-0">
                  {currentUser.displayName ? currentUser.displayName.slice(0, 2).toUpperCase() : (currentUser.email ? currentUser.email.slice(0, 2).toUpperCase() : 'OP')}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-semibold text-zinc-200 truncate font-heading">
                    {currentUser.displayName || currentUser.email?.split('@')[0] || 'Operator'}
                  </span>
                  <span className="text-[10px] font-mono text-[#FF3038] font-medium">
                    {isPro ? 'Friday Cyber Pro' : 'Free Operator'}
                  </span>
                </div>
              </div>

              <button
                onClick={onLogout}
                className="p-1.5 rounded-lg text-zinc-500 hover:text-[#FF3038] hover:bg-[#181820] transition-colors"
                title="Disconnect Session"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <button
                onClick={onOpenAuth}
                className="w-full py-2 px-3 rounded-xl bg-[#13131a] hover:bg-[#191924] border border-[#22222e] text-xs font-heading font-medium text-zinc-200 flex items-center justify-center gap-2 transition-colors"
              >
                <User className="w-3.5 h-3.5 text-[#FF3038]" />
                <span>Operator Sign In</span>
              </button>
              <button
                onClick={onOpenPricing}
                className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#FF3038]/20 to-[#990000]/20 hover:from-[#FF3038]/30 hover:to-[#990000]/30 border border-[#FF3038]/40 text-xs font-heading font-semibold text-rose-300 flex items-center justify-center gap-1.5 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5 text-[#FF3038]" />
                <span>Upgrade to Pro</span>
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

