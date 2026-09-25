import React, { useState, useRef, useEffect } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { Building2, ChevronDown, Check, Plus, Palette, Sparkles, Loader2 } from 'lucide-react';
import { Workspace } from '../types';
import { useToast } from './Toast';
import { getApiErrorMessage } from '../services/api';

interface WorkspaceSwitcherProps {
  onOpenBrandKit: () => void;
}

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ onOpenBrandKit }) => {
  const { workspaces, currentWorkspace, setCurrentWorkspace, createWorkspace, isLoadingWorkspaces } = useWorkspace();
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
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-200 transition-all text-sm font-medium shadow-sm group"
        title="Chuyển đổi không gian làm việc"
      >
        <div className="w-6 h-6 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 group-hover:text-indigo-300 transition-colors">
          <Building2 className="w-3.5 h-3.5" />
        </div>
        <div className="flex flex-col text-left">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold leading-none">
            Workspace
          </span>
          <span className="text-xs font-semibold text-slate-100 max-w-[130px] truncate mt-0.5">
            {currentWorkspace ? currentWorkspace.name : 'Chọn Workspace...'}
          </span>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 mt-2 w-72 bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl shadow-black/60 p-2 z-50 text-slate-200 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800/80 flex items-center justify-between">
            <span>Danh sách Workspace</span>
            <span className="text-[11px] font-normal px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
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
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 font-semibold'
                      : 'hover:bg-slate-800/70 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold ${
                        isActive
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {ws.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="truncate">{ws.name}</span>
                  </div>
                  {isActive && <Check className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />}
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="my-1 border-t border-slate-800/80" />

          {/* Actions */}
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onOpenBrandKit();
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/70 transition-all text-left"
            >
              <Palette className="w-4 h-4 text-violet-400" />
              <span>Cấu hình Brand Kit thương hiệu</span>
            </button>

            {!isCreating ? (
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-indigo-600/10 transition-all text-left"
              >
                <Plus className="w-4 h-4" />
                <span>Tạo Workspace mới...</span>
              </button>
            ) : (
              <form onSubmit={handleCreateSubmit} className="p-2 bg-slate-950/80 rounded-xl border border-slate-800 mt-1">
                <input
                  type="text"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  placeholder="Tên Workspace hoặc Brand..."
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 mb-2"
                  autoFocus
                />
                <div className="flex items-center justify-end gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreating(false);
                      setNewWorkspaceName('');
                    }}
                    className="px-2.5 py-1 rounded-md text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || !newWorkspaceName.trim()}
                    className="px-3 py-1 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-[11px] font-semibold text-white flex items-center gap-1 shadow-sm"
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
