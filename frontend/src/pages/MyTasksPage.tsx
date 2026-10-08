import React, { useState, useEffect, useCallback } from 'react';
import { CheckCircle2, Clock, AlertCircle, Calendar, Plus, Search, Tag, Check, RotateCcw } from 'lucide-react';
import { Task, TaskStatus, TaskPriority, TaskType, Campaign, Page } from '../types';
import { taskApi, campaignApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { Pagination } from '../components/Pagination';

interface MyTasksPageProps {
  onNavigateToCampaign?: (campaignId: number) => void;
}

const EMPTY_PAGE: Page<Task> = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0,
  has_next: false,
  has_prev: false,
};

export const MyTasksPage: React.FC<MyTasksPageProps> = ({ onNavigateToCampaign }) => {
  const toast = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskPage, setTaskPage] = useState<Page<Task>>(EMPTY_PAGE);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [campaignFilter, setCampaignFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Form tạo task mới
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDescription, setNewTaskDescription] = useState('');
  const [newTaskCampaignId, setNewTaskCampaignId] = useState<number>(1);
  const [newTaskType, setNewTaskType] = useState<TaskType>('CONTENT');
  const [newTaskPriority, setNewTaskPriority] = useState<TaskPriority>('MEDIUM');
  const [newTaskDueDate, setNewTaskDueDate] = useState<string>(
    new Date(Date.now() + 86400000 * 2).toISOString().split('T')[0]
  );

  const todayStr = new Date().toISOString().split('T')[0];

  // Dải chiến dịch -> tham số `status`/`due` mà backend hiểu.
  //
  // `ALL` / `TODAY` / `OVERDUE` không phải trạng thái thật của Task, nên phải ánh
  // xạ thành `due=today` / `due=overdue` thay vì gửi thẳng `status=OVERDUE`
  // (sẽ trả về 0 dòng). `include_completed=false` dùng cho các trạng thái
  // "còn việc" để tác vụ DONE không lọn vào danh sách việc cần làm.
  const taskQuery = useCallback(() => {
    const statusValues = ['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE'];
    if (statusFilter === 'TODAY' || statusFilter === 'OVERDUE') {
      return { due: statusFilter.toLowerCase() as 'today' | 'overdue' };
    }
    const params: {
      status?: string;
      priority?: string;
      include_completed?: boolean;
      campaign_id?: number;
      search?: string;
      due?: 'today' | 'overdue';
    } = {};
    if (statusFilter !== 'ALL') {
      params.status = statusFilter;
      if (statusValues.includes(statusFilter) && statusFilter !== 'DONE') {
        params.include_completed = false;
      }
    }
    if (priorityFilter !== 'ALL') params.priority = priorityFilter;
    if (campaignFilter !== 'ALL') params.campaign_id = Number(campaignFilter);
    if (searchQuery.trim()) params.search = searchQuery.trim();
    return params;
  }, [statusFilter, priorityFilter, campaignFilter, searchQuery]);

  // Lọc + phân trang ở SERVER. `total` do backend đếm trên tập đã lọc nên con số
  // "Hiển thị x–y trên z" luôn khớp với những gì server trả về.
  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const result = await taskApi.getMyTasksPage(page, pageSize, taskQuery());
      setTasks(result.items);
      setTaskPage(result);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi tải danh sách tác vụ');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, taskQuery, toast]);

  // Danh sách chiến dịch chỉ nạp một lần: nó là bộ lọc, không phải nội dung
  // phân trang, nên không cần cắt trang.
  const loadCampaigns = useCallback(async () => {
    const cList = await campaignApi.getAll().catch(() => []);
    setCampaigns(cList);
    if (cList.length > 0) setNewTaskCampaignId((prev) => prev || cList[0].id);
  }, []);

  // Thẻ thống kê không phụ thuộc bộ lọc đang chọn nên nạp một lần.
  const loadSummary = useCallback(async () => {
    try {
      setSummary(await taskApi.getMyTasksSummary());
    } catch {
      setSummary({ overdue: 0, today: 0, in_progress: 0, done: 0, total: 0 });
    }
  }, []);

  useEffect(() => {
    void loadCampaigns();
    void loadSummary();
  }, [loadCampaigns, loadSummary]);

  // Nạp dữ liệu lúc mount. Effect phải nằm SAU khai báo loadTasks: nếu đặt trước,
  // biến bị dùng trước khi khai báo và ESLint cũng không bắt được lỗi đó.
  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  // Đổi bất kỳ bộ lọc nào thì về lại trang 1, nếu không sẽ hỏng.
  useEffect(() => {
    setPage(1);
  }, [statusFilter, priorityFilter, campaignFilter, searchQuery]);

  const handlePageSizeChange = (nextSize: number) => {
    setPageSize(nextSize);
    setPage(1);
  };

  const handleUpdateStatus = async (task: Task, nextStatus: TaskStatus) => {
    try {
      const updated = await taskApi.updateTask(task.id, { status: nextStatus });
      setTasks(prev => prev.map(t => t.id === task.id ? updated : t));
      toast.success(`Đã cập nhật trạng thái: ${nextStatus}`);
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi cập nhật trạng thái');
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) {
      toast.error('Vui lòng nhập tiêu đề tác vụ');
      return;
    }

    try {
      setIsSubmitting(true);
      const created = await taskApi.createTask(newTaskCampaignId, {
        title: newTaskTitle.trim(),
        description: newTaskDescription.trim() || undefined,
        task_type: newTaskType,
        priority: newTaskPriority,
        due_date: newTaskDueDate || undefined,
        status: 'TODO'
      });
      setTasks(prev => [created, ...prev]);
      toast.success('Đã tạo tác vụ mới thành công!');
      setIsCreateModalOpen(false);
      setNewTaskTitle('');
      setNewTaskDescription('');
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi tạo tác vụ');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Danh sách đã được lọc ở server (`loadTasks`), nên `tasks` chính là nội dung
  // trang hiện tại — không lọc lần nữa ở client, nếu không `total` của bộ phân
  // trang sẽ mâu thuẫn với danh sách đang hiện.
  const filteredTasks = tasks;

  // Số liệu thẻ thống kê lấy từ endpoint summary (phạm vi toàn bộ), KHÔNG đếm
  // trên `tasks` — `tasks` chỉ là một trang.
  const [summary, setSummary] = useState({ overdue: 0, today: 0, in_progress: 0, done: 0, total: 0 });

  // Đếm nhanh
  const overdueCount = summary.overdue;
  const todayCount = summary.today;
  const inProgressCount = summary.in_progress;
  const doneCount = summary.done;

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Tác Vụ Của Tôi (My Work Today)</h2>
          <p className="text-xs text-slate-500 mt-1">
            Trung tâm quản lý công việc hàng ngày: theo dõi deadline, cập nhật tiến độ và hoàn thành mục tiêu chiến dịch.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-md shadow-indigo-600/20 transition-all cursor-pointer active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Tạo Tác Vụ Mới</span>
        </button>
      </div>

      {/* Quick Summary Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <button
          onClick={() => setStatusFilter(statusFilter === 'OVERDUE' ? 'ALL' : 'OVERDUE')}
          className={`p-4 rounded-xl border text-left transition-all ${
            statusFilter === 'OVERDUE'
              ? 'bg-rose-50 border-rose-300 ring-2 ring-rose-500/20'
              : 'bg-white border-slate-200/80 hover:border-rose-200 shadow-sm'
          }`}
        >
          <div className="flex items-center justify-between text-rose-600 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Quá Hạn</span>
            <AlertCircle className="w-4 h-4" />
          </div>
          <p className="text-2xl font-black text-rose-700">{overdueCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Cần xử lý khẩn cấp</p>
        </button>

        <button
          onClick={() => setStatusFilter(statusFilter === 'TODAY' ? 'ALL' : 'TODAY')}
          className={`p-4 rounded-xl border text-left transition-all ${
            statusFilter === 'TODAY'
              ? 'bg-amber-50 border-amber-300 ring-2 ring-amber-500/20'
              : 'bg-white border-slate-200/80 hover:border-amber-200 shadow-sm'
          }`}
        >
          <div className="flex items-center justify-between text-amber-600 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Hôm Nay</span>
            <Clock className="w-4 h-4" />
          </div>
          <p className="text-2xl font-black text-amber-700">{todayCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Hạn chót trong ngày</p>
        </button>

        <button
          onClick={() => setStatusFilter(statusFilter === 'IN_PROGRESS' ? 'ALL' : 'IN_PROGRESS')}
          className={`p-4 rounded-xl border text-left transition-all ${
            statusFilter === 'IN_PROGRESS'
              ? 'bg-indigo-50 border-indigo-300 ring-2 ring-indigo-500/20'
              : 'bg-white border-slate-200/80 hover:border-indigo-200 shadow-sm'
          }`}
        >
          <div className="flex items-center justify-between text-indigo-600 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Đang Làm</span>
            <RotateCcw className="w-4 h-4" />
          </div>
          <p className="text-2xl font-black text-indigo-700">{inProgressCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Đang triển khai</p>
        </button>

        <button
          onClick={() => setStatusFilter(statusFilter === 'DONE' ? 'ALL' : 'DONE')}
          className={`p-4 rounded-xl border text-left transition-all ${
            statusFilter === 'DONE'
              ? 'bg-emerald-50 border-emerald-300 ring-2 ring-emerald-500/20'
              : 'bg-white border-slate-200/80 hover:border-emerald-200 shadow-sm'
          }`}
        >
          <div className="flex items-center justify-between text-emerald-600 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Hoàn Thành</span>
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <p className="text-2xl font-black text-emerald-700">{doneCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Đã giải quyết xong</p>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm kiếm tác vụ theo tên, mô tả..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-slate-500 font-medium">Trạng thái:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white"
          >
            <option value="ALL">Tất cả ({tasks.length})</option>
            <option value="OVERDUE">Quá hạn ({overdueCount})</option>
            <option value="TODAY">Hôm nay ({todayCount})</option>
            <option value="TODO">Cần làm (TODO)</option>
            <option value="IN_PROGRESS">Đang làm (IN_PROGRESS)</option>
            <option value="IN_REVIEW">Đang review (IN_REVIEW)</option>
            <option value="DONE">Hoàn thành (DONE)</option>
          </select>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-slate-500 font-medium">Ưu tiên:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white"
          >
            <option value="ALL">Tất cả mức độ</option>
            <option value="URGENT">Khẩn cấp (URGENT)</option>
            <option value="HIGH">Cao (HIGH)</option>
            <option value="MEDIUM">Trung bình (MEDIUM)</option>
            <option value="LOW">Thấp (LOW)</option>
          </select>
        </div>

        {/* Campaign Filter */}
        {campaigns.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium">Chiến dịch:</span>
            <select
              value={campaignFilter}
              onChange={(e) => setCampaignFilter(e.target.value)}
              className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white max-w-[180px] truncate"
            >
              <option value="ALL">Tất cả chiến dịch</option>
              {campaigns.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Task List Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Clock className="w-6 h-6 mx-auto animate-spin mb-2 text-indigo-500" />
            Đang tải dữ liệu tác vụ...
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-slate-300" />
            Không có tác vụ nào phù hợp với bộ lọc hiện tại.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredTasks.map(task => {
              const isOverdue = task.due_date && task.due_date < todayStr && task.status !== 'DONE';
              const isDueToday = task.due_date === todayStr;

              return (
                <div
                  key={task.id}
                  className={`p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors ${
                    isOverdue ? 'bg-rose-50/20' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox Quick Done */}
                    <button
                      onClick={() => handleUpdateStatus(task, task.status === 'DONE' ? 'TODO' : 'DONE')}
                      className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-all cursor-pointer ${
                        task.status === 'DONE'
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-slate-300 hover:border-indigo-500 bg-white'
                      }`}
                      title={task.status === 'DONE' ? 'Đánh dấu chưa hoàn thành' : 'Đánh dấu hoàn thành'}
                    >
                      {task.status === 'DONE' && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </button>

                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`text-sm font-bold ${
                          task.status === 'DONE' ? 'line-through text-slate-400' : 'text-slate-900'
                        }`}>
                          {task.title}
                        </span>

                        {/* Task Type Badge */}
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {task.task_type}
                        </span>

                        {/* Priority Badge */}
                        <span className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded ${
                          task.priority === 'URGENT'
                            ? 'bg-rose-100 text-rose-700 border border-rose-200'
                            : task.priority === 'HIGH'
                            ? 'bg-amber-100 text-amber-700 border border-amber-200'
                            : task.priority === 'MEDIUM'
                            ? 'bg-blue-100 text-blue-700 border border-blue-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}>
                          {task.priority}
                        </span>
                      </div>

                      {task.description && (
                        <p className="text-xs text-slate-500 leading-relaxed max-w-2xl">
                          {task.description}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 pt-1">
                        {/* Dùng <button> gốc thay cho <span onClick> vì đây là liên kết điều hướng tới chiến dịch. */}
                        {task.campaign && (
                          <button
                            type="button"
                            onClick={() => onNavigateToCampaign?.(task.campaign_id)}
                            className="font-medium text-indigo-600 hover:underline cursor-pointer flex items-center gap-1 text-left"
                          >
                            <Tag className="w-3 h-3" />
                            {task.campaign.name}
                          </button>
                        )}

                        {task.due_date && (
                          <span className={`flex items-center gap-1 font-semibold ${
                            isOverdue
                              ? 'text-rose-600'
                              : isDueToday
                              ? 'text-amber-600'
                              : 'text-slate-500'
                          }`}>
                            <Calendar className="w-3 h-3" />
                            Hạn: {task.due_date} {isOverdue && '(Quá hạn)'} {isDueToday && '(Hôm nay)'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions / Status Picker */}
                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    <select
                      value={task.status}
                      onChange={(e) => handleUpdateStatus(task, e.target.value as TaskStatus)}
                      className={`text-xs font-bold px-2.5 py-1.5 rounded-lg border cursor-pointer outline-none ${
                        task.status === 'DONE'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : task.status === 'IN_PROGRESS'
                          ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                          : task.status === 'IN_REVIEW'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-slate-50 text-slate-700 border-slate-200'
                      }`}
                    >
                      <option value="TODO">Cần làm (TODO)</option>
                      <option value="IN_PROGRESS">Đang làm (IN_PROGRESS)</option>
                      <option value="IN_REVIEW">Chờ review (IN_REVIEW)</option>
                      <option value="DONE">Hoàn thành (DONE)</option>
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Bộ phân trang chỉ hiện khi còn bản ghi — màn hình trống thì không có
            thanh "Trang 1/1" vô nghĩa. */}
        {!loading && filteredTasks.length > 0 && (
          <Pagination
            page={taskPage}
            onPageChange={setPage}
            onPageSizeChange={handlePageSizeChange}
            itemLabel="tác vụ"
            disabled={loading}
          />
        )}
      </div>

      {/* Modal Tạo Tác Vụ Mới */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-base font-black text-slate-900">Tạo Tác Vụ Mới Cho Chiến Dịch</h3>
              <button 
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Chiến dịch mục tiêu <span className="text-rose-500">*</span>
                </label>
                <select
                  value={newTaskCampaignId}
                  onChange={(e) => setNewTaskCampaignId(Number(e.target.value))}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white"
                  required
                >
                  {campaigns.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Tiêu đề tác vụ <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="Ví dụ: Thiết kế banner quảng cáo Facebook 1200x628"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Mô tả chi tiết / Yêu cầu
                </label>
                <textarea
                  rows={3}
                  placeholder="Yêu cầu cụ thể, liên kết tài liệu thiết kế hoặc ghi chú..."
                  value={newTaskDescription}
                  onChange={(e) => setNewTaskDescription(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Loại tác vụ</label>
                  <select
                    value={newTaskType}
                    onChange={(e) => setNewTaskType(e.target.value as TaskType)}
                    className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white"
                  >
                    <option value="CONTENT">Nội dung (CONTENT)</option>
                    <option value="DESIGN">Thiết kế (DESIGN)</option>
                    <option value="VIDEO">Video (VIDEO)</option>
                    <option value="ADS">Quảng cáo (ADS)</option>
                    <option value="RESEARCH">Nghiên cứu (RESEARCH)</option>
                    <option value="OTHER">Khác (OTHER)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Độ ưu tiên</label>
                  <select
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(e.target.value as TaskPriority)}
                    className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white"
                  >
                    <option value="LOW">Thấp (LOW)</option>
                    <option value="MEDIUM">Vừa (MEDIUM)</option>
                    <option value="HIGH">Cao (HIGH)</option>
                    <option value="URGENT">Khẩn cấp (URGENT)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Hạn hoàn thành</label>
                  <input
                    type="date"
                    value={newTaskDueDate}
                    onChange={(e) => setNewTaskDueDate(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm disabled:opacity-50"
                >
                  {isSubmitting ? 'Đang tạo...' : 'Tạo Tác Vụ'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
