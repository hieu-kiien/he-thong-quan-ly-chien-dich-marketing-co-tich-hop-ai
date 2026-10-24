import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Edit2,
  KeyRound,
  Trash2,
  AlertCircle,
  X,
} from 'lucide-react';
import { PageContainer } from '@/app/layout/PageContainer';
import {
  Button,
  IconButton,
  Card,
  CardHeader,
  CardBody,
  PageHeader,
  Tabs,
  TabPanel,
  Table,
  THead,
  TBody,
  TR,
  TH,
  TD,
  Badge,
  Dialog,
  ConfirmDialog,
  FormField,
  Input,
  Select,
  Textarea,
  Checkbox,
  useToast,
  ErrorState,
  SkeletonRows,
  Callout,
  type TabItem,
} from '@/components/ui';
import {
  authApi,
  usersApi,
  channelsApi,
  brandApi,
  assistantApi,
} from '@/lib/api/endpoints';
import { toApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth';
import { isManager } from '@/lib/permissions';
import { useDocumentTitle } from '@/lib/hooks';
import { formatDate } from '@/lib/format';
import { ROLE_LABEL } from '@/lib/labels';
import type {
  BrandProfileInput,
  Channel,
  ChannelCode,
  ChannelInput,
  Role,
  User,
  UserCreate,
  UserUpdate,
} from '@/lib/types';

type SettingsSection = 'account' | 'users' | 'channels' | 'brand' | 'ai';

export default function SettingsPage() {
  useDocumentTitle('Cài đặt hệ thống');
  const { section } = useParams<{ section?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();

  const isUserAdmin = isManager(user);
  const activeTab: SettingsSection =
    (section as SettingsSection) && ['account', 'users', 'channels', 'brand', 'ai'].includes(section as string)
      ? (section as SettingsSection)
      : 'account';

  const handleTabChange = (key: SettingsSection) => {
    navigate(key === 'account' ? '/settings' : `/settings/${key}`);
  };

  // Change password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // User management state
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserFullName, setNewUserFullName] = useState('');
  const [newUserRole, setNewUserRole] = useState<Role>('MARKETER');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [userFormError, setUserFormError] = useState<string | null>(null);

  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [resettingUser, setResettingUser] = useState<User | null>(null);
  const [resetPasswordVal, setResetPasswordVal] = useState('');

  // Channel management state
  const [isCreatingChannel, setIsCreatingChannel] = useState(false);
  const [newChannelCode, setNewChannelCode] = useState<ChannelCode>('FACEBOOK');
  const [newChannelName, setNewChannelName] = useState('');
  const [newChannelRules, setNewChannelRules] = useState('');
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [deletingChannel, setDeletingChannel] = useState<Channel | null>(null);
  const [channelDeleteConflict, setChannelDeleteConflict] = useState<string | null>(null);

  // Brand Profile state
  const [brandForm, setBrandForm] = useState<BrandProfileInput | null>(null);
  const [newBannedWord, setNewBannedWord] = useState('');
  const [newBannedNote, setNewBannedNote] = useState('');

  // Queries
  const usersQ = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list({ page: 1, page_size: 100 }),
    enabled: isUserAdmin && activeTab === 'users',
  });

  const channelsQ = useQuery({
    queryKey: ['channels', { include_inactive: true }],
    queryFn: () => channelsApi.list(true),
    enabled: isUserAdmin && activeTab === 'channels',
  });

  const brandQ = useQuery({
    queryKey: ['brand-profile'],
    queryFn: async () => {
      const data = await brandApi.get();
      setBrandForm({
        brand_name: data.brand_name,
        description: data.description,
        tone_of_voice: data.tone_of_voice,
        target_audience: data.target_audience,
        guidelines: data.guidelines,
        banned_keywords: data.banned_keywords.map((b) => ({ keyword: b.keyword, note: b.note })),
      });
      return data;
    },
    enabled: isUserAdmin && activeTab === 'brand',
  });

  const aiStatusQ = useQuery({
    queryKey: ['assistant', 'status'],
    queryFn: () => assistantApi.status(),
    enabled: isUserAdmin && activeTab === 'ai',
  });

  // Mutations
  const changePasswordMutation = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      toast.success('Đổi mật khẩu thành công');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordError(null);
    },
    onError: (err) => {
      setPasswordError(toApiError(err).message);
    },
  });

  const createUserMutation = useMutation({
    mutationFn: (body: UserCreate) => usersApi.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('Tạo người dùng thành công');
      setIsCreatingUser(false);
      setNewUserEmail('');
      setNewUserFullName('');
      setNewUserPassword('');
      setUserFormError(null);
    },
    onError: (err) => {
      setUserFormError(toApiError(err).message);
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: UserUpdate }) => usersApi.update(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('Cập nhật người dùng thành công');
      setEditingUser(null);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi cập nhật');
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      usersApi.resetPassword(id, password),
    onSuccess: () => {
      toast.success('Đã đặt lại mật khẩu cho người dùng');
      setResettingUser(null);
      setResetPasswordVal('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi đặt lại mật khẩu');
    },
  });

  const createChannelMutation = useMutation({
    mutationFn: (body: ChannelInput) => channelsApi.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Thêm kênh mới thành công');
      setIsCreatingChannel(false);
      setNewChannelName('');
      setNewChannelRules('');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi thêm kênh');
    },
  });

  const updateChannelMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: ChannelInput }) => channelsApi.update(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Cập nhật kênh thành công');
      setEditingChannel(null);
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi cập nhật');
    },
  });

  const deleteChannelMutation = useMutation({
    mutationFn: (id: number) => channelsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Đã xoá kênh');
      setDeletingChannel(null);
      setChannelDeleteConflict(null);
    },
    onError: (err) => {
      const apiErr = toApiError(err);
      if (apiErr.code === 'CHANNEL_IN_USE' || apiErr.status === 409) {
        setChannelDeleteConflict(
          'Kênh này đã được sử dụng trong các chiến dịch hoặc bài viết, không thể xoá hoàn toàn. Bạn có thể tắt trạng thái hoạt động của kênh.'
        );
      } else {
        toast.apiError(err, 'Lỗi xoá kênh');
      }
    },
  });

  const saveBrandMutation = useMutation({
    mutationFn: (body: BrandProfileInput) => brandApi.update(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brand-profile'] });
      toast.success('Cập nhật hồ sơ thương hiệu thành công');
    },
    onError: (err) => {
      toast.apiError(err, 'Lỗi lưu hồ sơ');
    },
  });

  // Tabs setup
  const tabItems: TabItem<SettingsSection>[] = [
    { key: 'account', label: 'Tài khoản cá nhân' },
    ...(isUserAdmin
      ? [
          { key: 'users' as const, label: 'Người dùng' },
          { key: 'channels' as const, label: 'Kênh tiếp thị' },
          { key: 'brand' as const, label: 'Hồ sơ thương hiệu' },
          { key: 'ai' as const, label: 'Trạng thái AI' },
        ]
      : []),
  ];

  return (
    <PageContainer>
      <PageHeader
        title="Cài đặt hệ thống"
        description="Quản lý tài khoản cá nhân, phân quyền thành viên, kênh phân phối và tiêu chuẩn thương hiệu."
      />

      <Tabs items={tabItems} value={activeTab} onChange={handleTabChange} />

      {/* 1. TÀI KHOẢN CÁ NHÂN */}
      {activeTab === 'account' && (
        <TabPanel tabKey="account" className="mt-6 space-y-6 max-w-2xl">
          <Card>
            <CardHeader title="Thông tin người dùng" />
            <CardBody className="space-y-3 text-sm">
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-fg-muted">Họ và tên:</span>
                <span className="font-semibold text-fg">{user?.full_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-fg-muted">Địa chỉ email:</span>
                <span className="font-mono text-fg">{user?.email}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-fg-muted">Vai trò trong hệ thống:</span>
                <Badge tone="accent">{user ? ROLE_LABEL[user.role] : '—'}</Badge>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Đổi mật khẩu"
              description="Để đảm bảo an toàn, vui lòng chọn mật khẩu mạnh gồm chữ, số và ký tự đặc biệt."
            />
            <CardBody>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!currentPassword) {
                    setPasswordError('Vui lòng nhập mật khẩu hiện tại.');
                    return;
                  }
                  if (newPassword.length < 6) {
                    setPasswordError('Mật khẩu mới tối thiểu 6 ký tự.');
                    return;
                  }
                  if (newPassword !== confirmPassword) {
                    setPasswordError('Mật khẩu xác nhận không khớp.');
                    return;
                  }
                  changePasswordMutation.mutate({
                    current_password: currentPassword,
                    new_password: newPassword,
                  });
                }}
                className="space-y-4"
              >
                {passwordError && <Callout tone="danger">{passwordError}</Callout>}

                <FormField label="Mật khẩu hiện tại" required>
                  {(p) => (
                    <Input
                      {...p}
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                    />
                  )}
                </FormField>

                <FormField label="Mật khẩu mới" required>
                  {(p) => (
                    <Input
                      {...p}
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                  )}
                </FormField>

                <FormField label="Xác nhận mật khẩu mới" required>
                  {(p) => (
                    <Input
                      {...p}
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                  )}
                </FormField>

                <div className="flex justify-end pt-2">
                  <Button
                    variant="primary"
                    type="submit"
                    loading={changePasswordMutation.isPending}
                  >
                    Đổi mật khẩu
                  </Button>
                </div>
              </form>
            </CardBody>
          </Card>
        </TabPanel>
      )}

      {/* 2. QUẢN LÝ NGƯỜI DÙNG (MANAGER ONLY) */}
      {isUserAdmin && activeTab === 'users' && (
        <TabPanel tabKey="users" className="mt-6 space-y-6">
          <Card>
            <CardHeader
              title="Danh sách người dùng"
              description="Quản lý tài khoản đăng nhập và phân quyền nhân sự marketing."
              actions={
                <Button variant="primary" size="sm" onClick={() => setIsCreatingUser(true)}>
                  <Plus className="h-4 w-4" />
                  Thêm thành viên
                </Button>
              }
            />

            {usersQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={4} />
              </div>
            ) : usersQ.isError ? (
              <ErrorState error={usersQ.error} onRetry={() => usersQ.refetch()} />
            ) : (
              <Table>
                <THead>
                  <TR>
                    <TH>Họ và tên</TH>
                    <TH>Email</TH>
                    <TH>Vai trò</TH>
                    <TH>Trạng thái</TH>
                    <TH>Ngày tạo</TH>
                    <TH className="text-right">Thao tác</TH>
                  </TR>
                </THead>
                <TBody>
                  {usersQ.data?.items.map((u) => {
                    const isSelf = u.id === user?.id;

                    return (
                      <TR key={u.id}>
                        <TD className="font-medium text-fg">
                          {u.full_name} {isSelf && <span className="text-xs text-fg-subtle">(Bạn)</span>}
                        </TD>
                        <TD className="font-mono text-xs">{u.email}</TD>
                        <TD>
                          <Badge tone={u.role === 'MANAGER' ? 'accent' : 'neutral'}>
                            {ROLE_LABEL[u.role]}
                          </Badge>
                        </TD>
                        <TD>
                          <Badge tone={u.is_active ? 'success' : 'danger'}>
                            {u.is_active ? 'Đang hoạt động' : 'Đã khoá'}
                          </Badge>
                        </TD>
                        <TD className="text-xs text-fg-muted">{formatDate(u.created_at)}</TD>
                        <TD className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <IconButton
                              label="Chỉnh sửa thông tin"
                              size="sm"
                              variant="ghost"
                              onClick={() => setEditingUser(u)}
                            >
                              <Edit2 className="h-4 w-4" />
                            </IconButton>
                            <IconButton
                              label="Đặt lại mật khẩu"
                              size="sm"
                              variant="ghost"
                              onClick={() => setResettingUser(u)}
                            >
                              <KeyRound className="h-4 w-4" />
                            </IconButton>
                          </div>
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>
            )}
          </Card>
        </TabPanel>
      )}

      {/* 3. KÊNH TIẾP THỊ (MANAGER ONLY) */}
      {isUserAdmin && activeTab === 'channels' && (
        <TabPanel tabKey="channels" className="mt-6 space-y-6">
          <Card>
            <CardHeader
              title="Danh mục kênh truyền thông"
              description="Các kênh đăng tải bài viết và tiếp nhận số liệu marketing."
              actions={
                <Button variant="primary" size="sm" onClick={() => setIsCreatingChannel(true)}>
                  <Plus className="h-4 w-4" />
                  Thêm kênh
                </Button>
              }
            />

            {channelsQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={4} />
              </div>
            ) : channelsQ.isError ? (
              <ErrorState error={channelsQ.error} onRetry={() => channelsQ.refetch()} />
            ) : (
              <Table>
                <THead>
                  <TR>
                    <TH>Tên kênh</TH>
                    <TH>Mã kênh</TH>
                    <TH>Quy chuẩn định dạng (gợi ý cho AI)</TH>
                    <TH>Trạng thái</TH>
                    <TH className="text-right">Thao tác</TH>
                  </TR>
                </THead>
                <TBody>
                  {channelsQ.data?.map((ch) => (
                    <TR key={ch.id}>
                      <TD className="font-medium text-fg">{ch.name}</TD>
                      <TD>
                        <Badge tone="neutral">{ch.code}</Badge>
                      </TD>
                      <TD className="text-xs text-fg-muted max-w-xs truncate">
                        {ch.format_rules || '—'}
                      </TD>
                      <TD>
                        <Badge tone={ch.is_active ? 'success' : 'neutral'}>
                          {ch.is_active ? 'Hoạt động' : 'Ngừng dùng'}
                        </Badge>
                      </TD>
                      <TD className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <IconButton
                            label="Chỉnh sửa kênh"
                            size="sm"
                            variant="ghost"
                            onClick={() => setEditingChannel(ch)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </IconButton>
                          <IconButton
                            label="Xoá kênh"
                            size="sm"
                            variant="ghost"
                            className="text-danger hover:bg-danger/10"
                            onClick={() => {
                              setDeletingChannel(ch);
                              setChannelDeleteConflict(null);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </IconButton>
                        </div>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </Card>
        </TabPanel>
      )}

      {/* 4. HỒ SƠ THƯƠNG HIỆU & TỪ CẤM (MANAGER ONLY) */}
      {isUserAdmin && activeTab === 'brand' && (
        <TabPanel tabKey="brand" className="mt-6 space-y-6">
          {brandQ.isLoading || !brandForm ? (
            <div className="space-y-4">
              <SkeletonRows rows={4} />
            </div>
          ) : brandQ.isError ? (
            <ErrorState error={brandQ.error} onRetry={() => brandQ.refetch()} />
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader
                  title="Thông tin & Bản sắc thương hiệu"
                  description="Dữ liệu làm ngữ cảnh nền tảng cho việc sinh nội dung của Trợ lý AI."
                />
                <CardBody className="space-y-4">
                  <FormField label="Tên thương hiệu" required>
                    {(p) => (
                      <Input
                        {...p}
                        value={brandForm.brand_name}
                        onChange={(e) => setBrandForm({ ...brandForm, brand_name: e.target.value })}
                      />
                    )}
                  </FormField>

                  <FormField label="Mô tả thương hiệu">
                    {(p) => (
                      <Textarea
                        {...p}
                        rows={3}
                        value={brandForm.description}
                        onChange={(e) => setBrandForm({ ...brandForm, description: e.target.value })}
                      />
                    )}
                  </FormField>

                  <FormField label="Giọng văn (Tone of voice)">
                    {(p) => (
                      <Input
                        {...p}
                        value={brandForm.tone_of_voice}
                        onChange={(e) => setBrandForm({ ...brandForm, tone_of_voice: e.target.value })}
                        placeholder="Ví dụ: Thân thiện, chuyên nghiệp, truyền cảm hứng..."
                      />
                    )}
                  </FormField>

                  <FormField label="Đối tượng khách hàng trọng tâm">
                    {(p) => (
                      <Textarea
                        {...p}
                        rows={3}
                        value={brandForm.target_audience}
                        onChange={(e) => setBrandForm({ ...brandForm, target_audience: e.target.value })}
                        placeholder="Ví dụ: Giới trẻ 18-28 tuổi, nhân viên văn phòng năng động..."
                      />
                    )}
                  </FormField>

                  <FormField label="Hướng dẫn tuân thủ & quy tắc chung">
                    {(p) => (
                      <Textarea
                        {...p}
                        rows={4}
                        value={brandForm.guidelines}
                        onChange={(e) => setBrandForm({ ...brandForm, guidelines: e.target.value })}
                      />
                    )}
                  </FormField>

                  <div className="flex justify-end pt-2">
                    <Button
                      variant="primary"
                      loading={saveBrandMutation.isPending}
                      onClick={() => saveBrandMutation.mutate(brandForm)}
                    >
                      Lưu hồ sơ thương hiệu
                    </Button>
                  </div>
                </CardBody>
              </Card>

              {/* Banned Keywords Manager */}
              <Card>
                <CardHeader
                  title="Từ cấm theo quy định thương hiệu"
                  description="Các từ ngữ hoặc cụm từ bị cấm xuất hiện trong bài viết tiếp thị (ví dụ: 'cam kết 100%', 'chữa khỏi')."
                />
                <CardBody className="space-y-4">
                  <div className="flex flex-col gap-2 rounded-lg border border-border bg-subtle p-3">
                    <span className="text-xs font-semibold text-fg">Thêm từ cấm mới:</span>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Từ cấm (vd: rẻ nhất, cam kết 100%)..."
                        value={newBannedWord}
                        onChange={(e) => setNewBannedWord(e.target.value)}
                      />
                      <Button
                        variant="secondary"
                        onClick={() => {
                          const kw = newBannedWord.trim().toLowerCase();
                          if (!kw) return;
                          if (brandForm.banned_keywords.some((b) => b.keyword === kw)) {
                            toast.error('Từ cấm này đã tồn tại trong danh sách');
                            return;
                          }
                          const updated = [
                            ...brandForm.banned_keywords,
                            { keyword: kw, note: newBannedNote.trim() || undefined },
                          ];
                          setBrandForm({ ...brandForm, banned_keywords: updated });
                          saveBrandMutation.mutate({ ...brandForm, banned_keywords: updated });
                          setNewBannedWord('');
                          setNewBannedNote('');
                        }}
                      >
                        Thêm
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-fg-muted">
                      Danh sách từ cấm hiện hành ({brandForm.banned_keywords.length}):
                    </span>
                    <div className="max-h-80 overflow-y-auto space-y-2 rounded border border-border p-2">
                      {brandForm.banned_keywords.length === 0 ? (
                        <p className="py-4 text-center text-xs text-fg-muted">Chưa có từ cấm nào được thiết lập.</p>
                      ) : (
                        brandForm.banned_keywords.map((b, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between rounded bg-surface p-2 text-xs border border-border"
                          >
                            <span className="font-mono font-medium text-danger">{b.keyword}</span>
                            <IconButton
                              label="Xoá từ cấm"
                              size="sm"
                              variant="ghost"
                              className="text-danger hover:bg-danger/10"
                              onClick={() => {
                                const updated = brandForm.banned_keywords.filter((_, i) => i !== idx);
                                setBrandForm({ ...brandForm, banned_keywords: updated });
                                saveBrandMutation.mutate({ ...brandForm, banned_keywords: updated });
                              }}
                            >
                              <X className="h-3 w-3" />
                            </IconButton>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            </div>
          )}
        </TabPanel>
      )}

      {/* 5. TRẠNG THÁI AI (MANAGER ONLY) */}
      {isUserAdmin && activeTab === 'ai' && (
        <TabPanel tabKey="ai" className="mt-6 space-y-6 max-w-2xl">
          <Card>
            <CardHeader
              title="Trạng thái dịch vụ AI Runner"
              description="Theo dõi tình trạng kết nối tiến trình OpenCode và năng lực xử lý tác vụ thông minh."
              actions={
                <Button variant="ghost" size="sm" onClick={() => aiStatusQ.refetch()}>
                  Làm mới
                </Button>
              }
            />
            <CardBody>
              {aiStatusQ.isLoading ? (
                <SkeletonRows rows={3} />
              ) : aiStatusQ.isError ? (
                <ErrorState error={aiStatusQ.error} onRetry={() => aiStatusQ.refetch()} />
              ) : aiStatusQ.data ? (
                <div className="space-y-4 text-sm">
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-fg-muted">Khả dụng của Trợ lý AI:</span>
                    <Badge tone={aiStatusQ.data.available ? 'success' : 'danger'}>
                      {aiStatusQ.data.available ? 'Đang sẵn sàng' : 'Không khả dụng'}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-fg-muted">Tiến trình AI Runner (Cổng 8100):</span>
                    <span className="font-medium text-fg">
                      {aiStatusQ.data.runner.ok ? 'Kết nối thành công (OK)' : 'Mất kết nối'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-fg-muted">Mô hình OpenCode sử dụng:</span>
                    <span className="font-mono text-fg">
                      {aiStatusQ.data.runner.model || 'OpenCode Zen (Free)'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-fg-muted">Hàng đợi xử lý:</span>
                    <span className="font-mono font-semibold text-fg">
                      {aiStatusQ.data.queue_length} lượt yêu cầu
                    </span>
                  </div>

                  {aiStatusQ.data.last_error && (
                    <Callout tone="warning" title="Ghi nhận lỗi gần nhất:">
                      <p className="font-mono text-xs text-danger">{aiStatusQ.data.last_error}</p>
                    </Callout>
                  )}
                </div>
              ) : null}
            </CardBody>
          </Card>
        </TabPanel>
      )}

      {/* Create User Dialog */}
      <Dialog
        open={isCreatingUser}
        onClose={() => setIsCreatingUser(false)}
        title="Thêm người dùng mới"
        size="md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!newUserEmail.trim()) {
              setUserFormError('Vui lòng nhập email.');
              return;
            }
            if (!newUserFullName.trim()) {
              setUserFormError('Vui lòng nhập họ và tên.');
              return;
            }
            if (newUserPassword.length < 6) {
              setUserFormError('Mật khẩu tối thiểu 6 ký tự.');
              return;
            }
            createUserMutation.mutate({
              email: newUserEmail.trim().toLowerCase(),
              full_name: newUserFullName.trim(),
              role: newUserRole,
              password: newUserPassword,
            });
          }}
          className="space-y-4"
        >
          {userFormError && <Callout tone="danger">{userFormError}</Callout>}

          <FormField label="Họ và tên" required>
            {(p) => (
              <Input
                {...p}
                value={newUserFullName}
                onChange={(e) => setNewUserFullName(e.target.value)}
                placeholder="Nguyễn Văn A"
              />
            )}
          </FormField>

          <FormField label="Email" required>
            {(p) => (
              <Input
                {...p}
                type="email"
                value={newUserEmail}
                onChange={(e) => setNewUserEmail(e.target.value)}
                placeholder="ten@marketflow.vn"
              />
            )}
          </FormField>

          <FormField label="Vai trò" required>
            {(p) => (
              <Select
                {...p}
                value={newUserRole}
                onChange={(e) => setNewUserRole(e.target.value as Role)}
                options={[
                  { value: 'MARKETER', label: ROLE_LABEL.MARKETER },
                  { value: 'MANAGER', label: ROLE_LABEL.MANAGER },
                ]}
              />
            )}
          </FormField>

          <FormField label="Mật khẩu khởi tạo" required>
            {(p) => (
              <Input
                {...p}
                type="password"
                value={newUserPassword}
                onChange={(e) => setNewUserPassword(e.target.value)}
              />
            )}
          </FormField>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsCreatingUser(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createUserMutation.isPending}>
              Tạo người dùng
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog
        open={!!editingUser}
        onClose={() => setEditingUser(null)}
        title={`Chỉnh sửa người dùng: ${editingUser?.full_name}`}
        size="md"
      >
        {editingUser && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateUserMutation.mutate({
                id: editingUser.id,
                body: {
                  full_name: editingUser.full_name,
                  role: editingUser.role,
                  is_active: editingUser.is_active,
                },
              });
            }}
            className="space-y-4"
          >
            <FormField label="Họ và tên" required>
              {(p) => (
                <Input
                  {...p}
                  value={editingUser.full_name}
                  onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
                />
              )}
            </FormField>

            <FormField label="Vai trò" required>
              {(p) => (
                <Select
                  {...p}
                  disabled={editingUser.id === user?.id}
                  value={editingUser.role}
                  onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value as Role })}
                  options={[
                    { value: 'MARKETER', label: ROLE_LABEL.MARKETER },
                    { value: 'MANAGER', label: ROLE_LABEL.MANAGER },
                  ]}
                />
              )}
            </FormField>

            <div className="pt-2">
              <Checkbox
                label="Cho phép tài khoản hoạt động"
                disabled={editingUser.id === user?.id}
                checked={editingUser.is_active}
                onChange={(e) => setEditingUser({ ...editingUser, is_active: e.target.checked })}
              />
              {editingUser.id === user?.id && (
                <p className="mt-1 text-xs text-fg-subtle">Bạn không thể tự khoá hoặc hạ quyền chính mình.</p>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setEditingUser(null)}>
                Huỷ
              </Button>
              <Button variant="primary" type="submit" loading={updateUserMutation.isPending}>
                Lưu thay đổi
              </Button>
            </div>
          </form>
        )}
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog
        open={!!resettingUser}
        onClose={() => setResettingUser(null)}
        title={`Đặt lại mật khẩu: ${resettingUser?.full_name}`}
        size="md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (resetPasswordVal.length < 6) {
              toast.error('Mật khẩu mới tối thiểu 6 ký tự');
              return;
            }
            if (resettingUser) {
              resetPasswordMutation.mutate({
                id: resettingUser.id,
                password: resetPasswordVal,
              });
            }
          }}
          className="space-y-4"
        >
          <FormField label="Mật khẩu mới" required>
            {(p) => (
              <Input
                {...p}
                type="password"
                value={resetPasswordVal}
                onChange={(e) => setResetPasswordVal(e.target.value)}
                placeholder="Nhập mật khẩu mới cho người dùng..."
              />
            )}
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setResettingUser(null)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={resetPasswordMutation.isPending}>
              Đặt lại mật khẩu
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Create Channel Dialog */}
      <Dialog
        open={isCreatingChannel}
        onClose={() => setIsCreatingChannel(false)}
        title="Thêm kênh truyền thông mới"
        size="md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!newChannelName.trim()) {
              toast.error('Vui lòng nhập tên kênh');
              return;
            }
            createChannelMutation.mutate({
              code: newChannelCode,
              name: newChannelName.trim(),
              format_rules: newChannelRules.trim() || null,
              is_active: true,
            });
          }}
          className="space-y-4"
        >
          <FormField label="Mã kênh (Code)" required>
            {(p) => (
              <Select
                {...p}
                value={newChannelCode}
                onChange={(e) => setNewChannelCode(e.target.value as ChannelCode)}
                options={[
                  { value: 'FACEBOOK', label: 'FACEBOOK' },
                  { value: 'INSTAGRAM', label: 'INSTAGRAM' },
                  { value: 'TIKTOK', label: 'TIKTOK' },
                  { value: 'ZALO_OA', label: 'ZALO_OA' },
                  { value: 'EMAIL', label: 'EMAIL' },
                  { value: 'GOOGLE_ADS', label: 'GOOGLE_ADS' },
                  { value: 'WEBSITE', label: 'WEBSITE' },
                ]}
              />
            )}
          </FormField>

          <FormField label="Tên hiển thị kênh" required>
            {(p) => (
              <Input
                {...p}
                value={newChannelName}
                onChange={(e) => setNewChannelName(e.target.value)}
                placeholder="Ví dụ: Trang Facebook Fanpage chính..."
              />
            )}
          </FormField>

          <FormField label="Quy chuẩn định dạng (Gợi ý cho AI & người soạn)">
            {(p) => (
              <Textarea
                {...p}
                rows={3}
                value={newChannelRules}
                onChange={(e) => setNewChannelRules(e.target.value)}
                placeholder="Ví dụ: Giới hạn 200 từ, kèm 3-5 hashtag, giọng văn tự nhiên..."
              />
            )}
          </FormField>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsCreatingChannel(false)}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" loading={createChannelMutation.isPending}>
              Thêm kênh
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Edit Channel Dialog */}
      <Dialog
        open={!!editingChannel}
        onClose={() => setEditingChannel(null)}
        title={`Chỉnh sửa kênh: ${editingChannel?.name}`}
        size="md"
      >
        {editingChannel && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateChannelMutation.mutate({
                id: editingChannel.id,
                body: {
                  name: editingChannel.name,
                  format_rules: editingChannel.format_rules,
                  is_active: editingChannel.is_active,
                },
              });
            }}
            className="space-y-4"
          >
            <FormField label="Tên kênh" required>
              {(p) => (
                <Input
                  {...p}
                  value={editingChannel.name}
                  onChange={(e) => setEditingChannel({ ...editingChannel, name: e.target.value })}
                />
              )}
            </FormField>

            <FormField label="Quy chuẩn định dạng">
              {(p) => (
                <Textarea
                  {...p}
                  rows={3}
                  value={editingChannel.format_rules || ''}
                  onChange={(e) => setEditingChannel({ ...editingChannel, format_rules: e.target.value })}
                />
              )}
            </FormField>

            <div className="pt-2">
              <Checkbox
                label="Kênh đang hoạt động"
                checked={editingChannel.is_active}
                onChange={(e) => setEditingChannel({ ...editingChannel, is_active: e.target.checked })}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setEditingChannel(null)}>
                Huỷ
              </Button>
              <Button variant="primary" type="submit" loading={updateChannelMutation.isPending}>
                Lưu thay đổi
              </Button>
            </div>
          </form>
        )}
      </Dialog>

      {/* Delete Channel Confirm Dialog */}
      <ConfirmDialog
        open={!!deletingChannel}
        title={`Xoá kênh "${deletingChannel?.name}"`}
        confirmLabel={channelDeleteConflict ? 'Đóng' : 'Xác nhận xoá'}
        destructive={!channelDeleteConflict}
        loading={deleteChannelMutation.isPending}
        onClose={() => {
          setDeletingChannel(null);
          setChannelDeleteConflict(null);
        }}
        onConfirm={() => {
          if (channelDeleteConflict) {
            setDeletingChannel(null);
            setChannelDeleteConflict(null);
          } else if (deletingChannel) {
            deleteChannelMutation.mutate(deletingChannel.id);
          }
        }}
      >
        {channelDeleteConflict ? (
          <Callout tone="warning" icon={<AlertCircle className="h-5 w-5" />}>
            {channelDeleteConflict}
          </Callout>
        ) : (
          <p className="text-sm text-fg-muted">
            Hành động này sẽ xoá kênh nếu chưa có dữ liệu chiến dịch gắn liền. Bạn có chắc chắn muốn xoá?
          </p>
        )}
      </ConfirmDialog>
    </PageContainer>
  );
}
