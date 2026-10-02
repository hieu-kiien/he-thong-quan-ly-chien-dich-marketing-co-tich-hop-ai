import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { Workspace, BrandKit } from '../types';
import { workspaceApi, brandKitApi, getApiErrorMessage } from '../services/api';
import { useAuth } from './AuthContext';

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  brandKit: BrandKit | null;
  isLoadingWorkspaces: boolean;
  isLoadingBrandKit: boolean;
  brandKitError: string | null;
  workspaceError: string | null;
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
  const [brandKitError, setBrandKitError] = useState<string | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const loadBrandKit = useCallback(async (workspaceId: number) => {
    setIsLoadingBrandKit(true);
    try {
      const kit = await brandKitApi.getByWorkspace(workspaceId);
      setBrandKit(kit);
      setBrandKitError(null);
    } catch (err) {
      // Không nuốt lỗi: báo ra để App hiển thị trạng thái lỗi thay vì
      // hiển thị Brand Kit rỗng như thể người dùng chưa cấu hình gì.
      setBrandKitError(getApiErrorMessage(err));
      console.error('Lỗi khi nạp Brand Kit:', err);
    } finally {
      setIsLoadingBrandKit(false);
    }
  }, []);

  const setCurrentWorkspace = useCallback((workspace: Workspace) => {
    setCurrentWorkspaceState(workspace);
    localStorage.setItem('active_workspace_id', String(workspace.id));
    void loadBrandKit(workspace.id);
  }, [loadBrandKit]);

  const refreshWorkspaces = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoadingWorkspaces(true);
    try {
      const list = await workspaceApi.getAll();
      setWorkspaces(list);
      setWorkspaceError(null);

      // Chọn workspace đang lưu trong localStorage hoặc phần tử đầu tiên
      const savedId = localStorage.getItem('active_workspace_id');
      const found = list.find((w) => String(w.id) === savedId);
      const active = found || list[0] || null;

      setCurrentWorkspaceState(active);
      if (active) {
        localStorage.setItem('active_workspace_id', String(active.id));
        void loadBrandKit(active.id);
      } else {
        setBrandKit(null);
      }
    } catch (err) {
      setWorkspaceError(getApiErrorMessage(err));
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

  const refreshBrandKit = useCallback(async () => {
    if (currentWorkspace) {
      await loadBrandKit(currentWorkspace.id);
    }
  }, [currentWorkspace, loadBrandKit]);

  const updateBrandKit = useCallback(async (data: Partial<BrandKit>): Promise<BrandKit> => {
    if (!currentWorkspace) throw new Error('Chưa chọn không gian làm việc');
    const updated = await brandKitApi.update(currentWorkspace.id, data);
    setBrandKit(updated);
    return updated;
  }, [currentWorkspace]);

  const createWorkspace = useCallback(async (name: string, description?: string): Promise<Workspace> => {
    const created = await workspaceApi.create({ name, description });
    await refreshWorkspaces();
    setCurrentWorkspace(created);
    return created;
  }, [refreshWorkspaces, setCurrentWorkspace]);

  // Giá trị context phải ổn định theo referential equality: object literal mới mỗi
  // render khiến mọi useEffect phụ thuộc `useWorkspace()` chạy lại vô tình.
  const value = useMemo<WorkspaceContextType>(
    () => ({
      workspaces,
      currentWorkspace,
      brandKit,
      isLoadingWorkspaces,
      isLoadingBrandKit,
      brandKitError,
      workspaceError,
      setCurrentWorkspace,
      refreshWorkspaces,
      refreshBrandKit,
      updateBrandKit,
      createWorkspace,
    }),
    [
      workspaces,
      currentWorkspace,
      brandKit,
      isLoadingWorkspaces,
      isLoadingBrandKit,
      brandKitError,
      workspaceError,
      setCurrentWorkspace,
      refreshWorkspaces,
      refreshBrandKit,
      updateBrandKit,
      createWorkspace,
    ]
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
};

export const useWorkspace = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
