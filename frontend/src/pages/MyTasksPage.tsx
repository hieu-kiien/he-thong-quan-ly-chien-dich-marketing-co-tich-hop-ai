import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Calendar, 
  Filter, 
  Plus, 
  Search, 
  ChevronRight, 
  User as UserIcon,
  Tag,
  ArrowUpDown,
  Check,
  RotateCcw
} from 'lucide-react';
import { Task, TaskStatus, TaskPriority, TaskType, Campaign } from '../types';
import { taskApi, campaignApi, getApiErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';

interface MyTasksPageProps {
  onNavigateToCampaign?: (campaignId: number) => void;
}

export const MyTasksPage: React.FC<MyTasksPageProps> = ({ onNavigateToCampaign }) => {
  const toast = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
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

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [myTasks, cList] = await Promise.all([
        taskApi.getMyTasks({ include_completed: true }),
        campaignApi.getAll().catch(() => [])
      ]);
      setTasks(myTasks);
      setCampaigns(cList);
      if (cList.length > 0) {
        setNewTaskCampaignId(cList[0].id);
      }
    } catch (e: any) {
      toast.error(getApiErrorMessage(e), 'Lỗi tải danh sách tác vụ');
    } finally {
      setLoading(false);
    }
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

  // Lọc tác vụ
  const filteredTasks = tasks.filter(task => {
    if (statusFilter === 'TODO' && task.status !== 'TODO') return false;
    if (statusFilter === 'IN_PROGRESS' && task.status !== 'IN_PROGRESS') return false;
    if (statusFilter === 'IN_REVIEW' && task.status !== 'IN_REVIEW') return false;
    if (statusFilter === 'DONE' && task.status !== 'DONE') return false;
    if (statusFilter === 'OVERDUE') {
      const isOverdue = task.due_date && task.due_date < todayStr && task.status !== 'DONE';
      if (!isOverdue) return false;
    }
    if (statusFilter === 'TODAY') {
      if (task.due_date !== todayStr) return false;
    }

    if (priorityFilter !== 'ALL' && task.priority !== priorityFilter) return false;
    if (campaignFilter !== 'ALL' && task.campaign_id !== Number(campaignFilter)) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = task.title.toLowerCase().includes(q);
      const matchDesc = task.description?.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc) return false;
    }

    return true;
  });

  // Đếm nhanh
  const overdueCount = tasks.filter(t => t.due_date && t.due_date < todayStr && t.status !== 'DONE').length;
  const todayCount = tasks.filter(t => t.due_date === todayStr && t.status !== 'DONE').length;
  const inProgressCount = tasks.filter(t => t.status === 'IN_PROGRESS').length;
  const doneCount = tasks.filter(t => t.status === 'DONE').length;

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
              : 'bg-white border-slate-200/80 hover:border-rose-200 shadow-xs'
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
              : 'bg-white border-slate-200/80 hover:border-amber-200 shadow-xs'
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
              : 'bg-white border-slate-200/80 hover:border-indigo-200 shadow-xs'
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
              : 'bg-white border-slate-200/80 hover:border-emerald-200 shadow-xs'
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
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm kiếm tác vụ theo tên, mô tả..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg outline-hidden focus:border-indigo-500"
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
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
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
                        {task.campaign && (
                          <span 
                            onClick={() => onNavigateToCampaign?.(task.campaign_id)}
                            className="font-medium text-indigo-600 hover:underline cursor-pointer flex items-center gap-1"
                          >
                            <Tag className="w-3 h-3" />
                            {task.campaign.name}
                          </span>
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
                      className={`text-xs font-bold px-2.5 py-1.5 rounded-lg border cursor-pointer outline-hidden ${
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
      </div>

      {/* Modal Tạo Tác Vụ Mới */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
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
