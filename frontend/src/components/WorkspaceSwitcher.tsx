import React, { useState, useRef, useEffect } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { Building2, ChevronDown, Check, Plus, Palette, Loader2 } from 'lucide-react';
import { Workspace } from '../types';
import { useToast } from './Toast';
import { getApiErrorMessage } from '../services/api';

interface WorkspaceSwitcherProps {
  onOpenBrandKit: () => void;
}

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ onOpenBrandKit }) => {
  const { workspaces, currentWorkspace, setCurrentWorkspace, createWorkspace } = useWorkspace();
  const toast = useToast();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectWorkspace = (ws: Workspace) => {
    setCurrentWorkspace(ws);
    setIsOpen(false);
    setIsCreating(false);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    setIsSubmitting(true);
    try {
      await createWorkspace(newWorkspaceName.trim());
      toast.success(`Đã tạo không gian làm việc "${newWorkspaceName.trim()}" thành công!`);
      setNewWorkspaceName('');
      setIsCreating(false);
      setIsOpen(false);
    } catch (err: any) {
      toast.error(getApiErrorMessage(err), 'Không thể tạo Workspace mới');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Chuyển đổi không gian làm việc"
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex w-full items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#F6F5F0] hover:bg-[#EAE8E1] border border-[#E4E2DD] text-[#121316] transition-all text-xs font-medium group cursor-pointer"
        title="Chuyển đổi không gian làm việc"
      >
        <div className="w-6 h-6 shrink-0 rounded-md bg-[#121316] flex items-center justify-center text-white">
          <Building2 className="w-3.5 h-3.5" />
        </div>
        <div className="flex min-w-0 flex-col text-left">
          <span className="text-[9px] uppercase tracking-wider text-[#5A5E66] font-bold leading-none">
            Không gian
          </span>
          <span className="text-xs font-bold text-[#121316] truncate mt-0.5">
            {currentWorkspace ? currentWorkspace.name : 'Chọn không gian...'}
          </span>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 text-[#5A5E66] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 mt-2 w-72 bg-white border border-[#E4E2DD] rounded-xl shadow-xl p-2 z-50 text-[#121316]">
          <div className="px-3 py-2 text-[11px] font-bold text-[#5A5E66] uppercase tracking-wider border-b border-[#F0EFEA] flex items-center justify-between">
            <span>Không gian làm việc</span>
            <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-[#F6F5F0] text-[#121316] border border-[#E4E2DD]">
              {workspaces.length}
            </span>
          </div>

          {/* Workspaces List */}
          <div className="max-h-56 overflow-y-auto py-1 space-y-1">
            {workspaces.map((ws) => {
              const isActive = currentWorkspace?.id === ws.id;
              return (
                <button
                  key={ws.id}
                  type="button"
                  onClick={() => handleSelectWorkspace(ws)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    isActive
                      ? 'bg-[#FAF9F5] text-[#121316] border border-[#D95D39]/50 font-bold'
                      : 'hover:bg-[#F6F5F0] text-[#121316]'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <div
                      className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold ${
                        isActive
                          ? 'bg-[#D95D39] text-white'
                          : 'bg-[#F6F5F0] text-[#5A5E66] border border-[#E4E2DD]'
                      }`}
                    >
                      {ws.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="truncate">{ws.name}</span>
                  </div>
                  {isActive && <Check className="w-3.5 h-3.5 text-[#D95D39] flex-shrink-0" />}
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="my-1 border-t border-[#F0EFEA]" />

          {/* Actions */}
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onOpenBrandKit();
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-[#121316] hover:bg-[#F6F5F0] transition-all text-left cursor-pointer"
            >
              <Palette className="w-4 h-4 text-[#D95D39]" />
              <span>Quy chuẩn giọng văn thương hiệu</span>
            </button>

            {!isCreating ? (
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-bold text-[#D95D39] hover:bg-[#FAF9F5] transition-all text-left cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Tạo không gian mới...</span>
              </button>
            ) : (
              <form onSubmit={handleCreateSubmit} className="p-2 bg-[#FAF9F5] rounded-lg border border-[#E4E2DD] mt-1">
                <input
                  type="text"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  placeholder="Tên thương hiệu hoặc dự án..."
                  className="w-full bg-white border border-[#E4E2DD] rounded-lg px-2.5 py-1.5 text-xs text-[#121316] placeholder-[#8A8F98] focus:outline-none focus:border-[#121316] mb-2"
                  autoFocus
                />
                <div className="flex items-center justify-end gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreating(false);
                      setNewWorkspaceName('');
                    }}
                    className="px-2.5 py-1 rounded-md text-[11px] font-semibold text-[#5A5E66] hover:bg-[#EAE8E1]"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || !newWorkspaceName.trim()}
                    className="px-3 py-1 rounded-md bg-[#121316] hover:bg-black disabled:opacity-50 text-[11px] font-bold text-white flex items-center gap-1"
                  >
                    {isSubmitting ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Tạo'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
