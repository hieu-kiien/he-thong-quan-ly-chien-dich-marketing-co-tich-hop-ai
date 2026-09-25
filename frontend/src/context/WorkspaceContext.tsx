import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Workspace, BrandKit } from '../types';
import { workspaceApi, brandKitApi } from '../services/api';
import { useAuth } from './AuthContext';

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  brandKit: BrandKit | null;
  isLoadingWorkspaces: boolean;
  isLoadingBrandKit: boolean;
  setCurrentWorkspace: (workspace: Workspace) => void;
  refreshWorkspaces: () => Promise<void>;
  refreshBrandKit: () => Promise<void>;
  updateBrandKit: (data: Partial<BrandKit>) => Promise<BrandKit>;
  createWorkspace: (name: string, description?: string) => Promise<Workspace>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [brandKit, setBrandKit] = useState<BrandKit | null>(null);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState<boolean>(false);
  const [isLoadingBrandKit, setIsLoadingBrandKit] = useState<boolean>(false);

  const loadBrandKit = useCallback(async (workspaceId: number) => {
    setIsLoadingBrandKit(true);
    try {
      const kit = await brandKitApi.getByWorkspace(workspaceId);
      setBrandKit(kit);
    } catch (err) {
      console.error('Lỗi khi nạp Brand Kit:', err);
    } finally {
      setIsLoadingBrandKit(false);
    }
  }, []);

  const setCurrentWorkspace = (workspace: Workspace) => {
    setCurrentWorkspaceState(workspace);
    localStorage.setItem('active_workspace_id', String(workspace.id));
    loadBrandKit(workspace.id);
  };

  const refreshWorkspaces = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoadingWorkspaces(true);
    try {
      const list = await workspaceApi.getAll();
      setWorkspaces(list);

      // Chọn workspace đang lưu trong localStorage hoặc phần tử đầu tiên
      const savedId = localStorage.getItem('active_workspace_id');
      const found = list.find((w) => String(w.id) === savedId);
      const active = found || list[0] || null;

      setCurrentWorkspaceState(active);
      if (active) {
        localStorage.setItem('active_workspace_id', String(active.id));
        loadBrandKit(active.id);
      } else {
        setBrandKit(null);
      }
    } catch (err) {
      console.error('Lỗi khi nạp danh sách workspace:', err);
    } finally {
      setIsLoadingWorkspaces(false);
    }
  }, [isAuthenticated, loadBrandKit]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshWorkspaces();
    } else {
      setWorkspaces([]);
      setCurrentWorkspaceState(null);
      setBrandKit(null);
    }
  }, [isAuthenticated, refreshWorkspaces]);

  const refreshBrandKit = async () => {
    if (currentWorkspace) {
      await loadBrandKit(currentWorkspace.id);
    }
  };

  const updateBrandKit = async (data: Partial<BrandKit>): Promise<BrandKit> => {
    if (!currentWorkspace) throw new Error('Chưa chọn không gian làm việc');
    const updated = await brandKitApi.update(currentWorkspace.id, data);
    setBrandKit(updated);
    return updated;
  };

  const createWorkspace = async (name: string, description?: string): Promise<Workspace> => {
    const created = await workspaceApi.create({ name, description });
    await refreshWorkspaces();
    setCurrentWorkspace(created);
    return created;
  };

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        currentWorkspace,
        brandKit,
        isLoadingWorkspaces,
        isLoadingBrandKit,
        setCurrentWorkspace,
        refreshWorkspaces,
        refreshBrandKit,
        updateBrandKit,
        createWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
