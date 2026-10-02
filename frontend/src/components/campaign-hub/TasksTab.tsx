import React from 'react';
import { 
  ListTodo, 
  Plus, 
  Clock, 
  Check, 
  Trash2 
} from 'lucide-react';
import { Campaign, Task, TaskPriority, TaskStatus, TaskType } from '../../types';

interface TasksTabProps {
  campaign: Campaign | null;
  campaignTasks: Task[];
  loadingTasks: boolean;
  newTaskTitle: string;
  setNewTaskTitle: (val: string) => void;
  newTaskType: TaskType;
  setNewTaskType: (val: TaskType) => void;
  newTaskPriority: TaskPriority;
  setNewTaskPriority: (val: TaskPriority) => void;
  newTaskDueDate: string;
  setNewTaskDueDate: (val: string) => void;
  isCreatingTask: boolean;
  handleCreateCampaignTask: (e: React.FormEvent) => void;
  handleUpdateCampaignTaskStatus: (taskId: number, nextStatus: TaskStatus) => void;
  handleDeleteCampaignTask: (taskId: number) => void;
}

export const TasksTab: React.FC<TasksTabProps> = ({
  campaignTasks,
  loadingTasks,
  newTaskTitle,
  setNewTaskTitle,
  newTaskType,
  setNewTaskType,
  newTaskPriority,
  setNewTaskPriority,
  newTaskDueDate,
  setNewTaskDueDate,
  isCreatingTask,
  handleCreateCampaignTask,
  handleUpdateCampaignTaskStatus,
  handleDeleteCampaignTask,
}) => {
  return (
    <div className="space-y-6">
      {/* Quick Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 bg-white rounded-xl border border-slate-200 shadow">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Tổng Tác Vụ</span>
          <span className="text-xl font-extrabold text-slate-900 mt-1 block">{campaignTasks.length}</span>
        </div>
        <div className="p-3.5 bg-white rounded-xl border border-slate-200 shadow">
          <span className="text-[11px] font-bold text-rose-600 uppercase tracking-wider block">Quá Hạn</span>
          <span className="text-xl font-extrabold text-rose-600 mt-1 block">
            {campaignTasks.filter(t => t.due_date && new Date(t.due_date) < new Date() && t.status !== 'DONE').length}
          </span>
        </div>
        <div className="p-3.5 bg-white rounded-xl border border-slate-200 shadow">
          <span className="text-[11px] font-bold text-blue-600 uppercase tracking-wider block">Đang Làm</span>
          <span className="text-xl font-extrabold text-blue-600 mt-1 block">
            {campaignTasks.filter(t => t.status === 'IN_PROGRESS').length}
          </span>
        </div>
        <div className="p-3.5 bg-white rounded-xl border border-slate-200 shadow">
          <span className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider block">Đã Xong</span>
          <span className="text-xl font-extrabold text-emerald-600 mt-1 block">
            {campaignTasks.filter(t => t.status === 'DONE').length}
          </span>
        </div>
      </div>

      {/* Quick Create Task Form */}
      <form onSubmit={handleCreateCampaignTask} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Plus className="w-4 h-4 text-indigo-600" />
            Thêm Tác Vụ Mới Cho Chiến Dịch Này
          </span>
          <span className="text-[10px] text-slate-500 font-medium">Phân công nhanh cho nhân sự marketing</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="lg:col-span-2">
            <input
              type="text"
              required
              placeholder="Tên tác vụ (vd: Thiết kế key visual Facebook Ads)..."
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-slate-800"
            />
          </div>

          <div>
            <select
              value={newTaskType}
              onChange={(e) => setNewTaskType(e.target.value as TaskType)}
              className="w-full text-xs p-2.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium"
            >
              <option value="CONTENT">Nội dung (Content)</option>
              <option value="DESIGN">Thiết kế (Design)</option>
              <option value="VIDEO">Video / Reels</option>
              <option value="ADS">Chạy Ads</option>
              <option value="RESEARCH">Nghiên cứu thị trường</option>
              <option value="OTHER">Khác</option>
            </select>
          </div>

          <div>
            <select
              value={newTaskPriority}
              onChange={(e) => setNewTaskPriority(e.target.value as TaskPriority)}
              className="w-full text-xs p-2.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium"
            >
              <option value="LOW">Ưu tiên Thấp</option>
              <option value="MEDIUM">Ưu tiên Vừa</option>
              <option value="HIGH">Ưu tiên Cao</option>
              <option value="URGENT">Khẩn cấp (Urgent)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="date"
              value={newTaskDueDate}
              onChange={(e) => setNewTaskDueDate(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-slate-200 bg-white text-slate-700"
            />
            <button
              type="submit"
              disabled={isCreatingTask || !newTaskTitle.trim()}
              className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-colors shrink-0 disabled:opacity-50"
            >
              {isCreatingTask ? '...' : '+ Thêm'}
            </button>
          </div>
        </div>
      </form>

      {/* Task List / Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Danh Sách Tác Vụ ({campaignTasks.length})
          </span>
          <span className="text-[11px] text-slate-500">
            1-click vào hộp kiểm hoặc menu trạng thái để chuyển giai đoạn
          </span>
        </div>

        {loadingTasks ? (
          <div className="p-8 text-center text-xs text-slate-500">Đang tải danh sách tác vụ...</div>
        ) : campaignTasks.length === 0 ? (
          <div className="p-10 text-center space-y-2">
            <ListTodo className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-xs font-bold text-slate-700">Chưa có tác vụ nào trong chiến dịch này</p>
            <p className="text-xs text-slate-500">
              Tạo tác vụ đầu tiên ở biểu mẫu phía trên để bắt đầu giao việc cho đội ngũ.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {campaignTasks.map((t) => {
              const isDone = t.status === 'DONE';
              const isOverdue = t.due_date && new Date(t.due_date) < new Date() && !isDone;
              return (
                <div
                  key={t.id}
                  className={`p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/70 transition-colors ${
                    isDone ? 'opacity-60 bg-slate-50/30' : ''
                  }`}
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <button
                      onClick={() => handleUpdateCampaignTaskStatus(t.id, isDone ? 'TODO' : 'DONE')}
                      className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 mt-0.5 sm:mt-0 transition-colors ${
                        isDone
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-slate-300 hover:border-indigo-500 bg-white'
                      }`}
                    >
                      {isDone && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </button>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                          {t.task_type}
                        </span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            t.priority === 'URGENT'
                              ? 'bg-rose-100 text-rose-700'
                              : t.priority === 'HIGH'
                              ? 'bg-amber-100 text-amber-700'
                              : t.priority === 'MEDIUM'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {t.priority}
                        </span>
                        {isOverdue && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                            Quá hạn
                          </span>
                        )}
                      </div>
                      <h4 className={`text-xs font-bold text-slate-800 mt-1 ${isDone ? 'line-through text-slate-400' : ''}`}>
                        {t.title}
                      </h4>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    {t.due_date && (
                      <div className={`text-[11px] flex items-center gap-1 font-medium ${isOverdue ? 'text-rose-600 font-bold' : 'text-slate-500'}`}>
                        <Clock className="w-3.5 h-3.5" />
                        <span>{new Date(t.due_date).toLocaleDateString('vi-VN')}</span>
                      </div>
                    )}

                    <select
                      value={t.status}
                      onChange={(e) => handleUpdateCampaignTaskStatus(t.id, e.target.value as TaskStatus)}
                      className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${
                        t.status === 'DONE'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : t.status === 'IN_PROGRESS'
                          ? 'bg-blue-50 text-blue-700 border-blue-200'
                          : t.status === 'IN_REVIEW'
                          ? 'bg-purple-50 text-purple-700 border-purple-200'
                          : 'bg-slate-50 text-slate-700 border-slate-200'
                      }`}
                    >
                      <option value="TODO">Cần Làm</option>
                      <option value="IN_PROGRESS">Đang Làm</option>
                      <option value="IN_REVIEW">Đang Duyệt</option>
                      <option value="DONE">Hoàn Thành</option>
                    </select>

                    <button
                      onClick={() => handleDeleteCampaignTask(t.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                      title="Xóa tác vụ"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
