import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Shield, 
  Zap, 
  Terminal, 
  Activity, 
  Settings, 
  History, 
  LogOut, 
  User, 
  Lock, 
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Menu,
  X,
  ChevronRight,
  Database
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { auth, tasks, discovery, getBaseUrl, setBaseUrl as persistBaseUrl } from './api';
import './App.css';

// Types
interface TaskResult {
  id: string;
  status: string;
  results?: Record<string, any>;
  last_error?: string | null;
  created_at?: string;
  updated_at?: string;
  message?: string;
  command?: string;
  submitted_at?: string;
}

interface Agent {
  agent_id: string;
  name: string;
  supported_protocols: string[];
  is_active: boolean;
}

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('engram_token'));
  const [isLoginView, setIsLoginView] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [activeTab, setActiveTab] = useState('orchestrate');
  const [taskInput, setTaskInput] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [taskHistory, setTaskHistory] = useState<TaskResult[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eat, setEat] = useState(localStorage.getItem('engram_eat'));
  const [baseUrl, setBaseUrl] = useState(getBaseUrl());
  const [baseUrlDraft, setBaseUrlDraft] = useState(getBaseUrl());

  const historyEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated) {
      loadAgents();
      loadRecentTasks();
      if (!eat) generateEat();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    scrollToBottom();
  }, [taskHistory]);

  const scrollToBottom = () => {
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadAgents = async () => {
    try {
      const data = await discovery.getAgents();
      setAgents(data);
    } catch (err) {
      console.error('Failed to load agents', err);
    }
  };

  const loadRecentTasks = async () => {
    try {
      const data = await tasks.list(20);
      const normalized = data.map((task: any) => ({
        id: task.id,
        status: task.status,
        results: task.results || undefined,
        last_error: task.last_error || null,
        created_at: task.created_at,
        updated_at: task.updated_at,
      }));
      setTaskHistory(normalized);
    } catch (err) {
      console.error('Failed to load tasks', err);
    }
  };

  const generateEat = async () => {
    try {
      const newEat = await auth.generateEat();
      setEat(newEat);
      setError(null);
    } catch (err) {
      setError('Failed to generate Engram Access Token.');
    }
  };

  const addTaskToHistory = (task: TaskResult) => {
    setTaskHistory(prev => [...prev, task]);
  };

  const updateTaskInHistory = (taskId: string, patch: Partial<TaskResult>) => {
    setTaskHistory(prev =>
      prev.map(task => (task.id === taskId ? { ...task, ...patch } : task))
    );
  };

  const pollTask = async (taskId: string) => {
    while (true) {
      try {
        const task = await tasks.get(taskId);
        updateTaskInHistory(taskId, {
          status: task.status,
          results: task.results || undefined,
          last_error: task.last_error || null,
          created_at: task.created_at,
          updated_at: task.updated_at,
        });
        if (task.status === 'COMPLETED' || task.status === 'DEAD_LETTER') {
          break;
        }
      } catch (err: any) {
        setError('Failed to refresh task status.');
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await auth.login(email, password);
      setIsAuthenticated(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.');
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await auth.signup({ email, password, user_metadata: { source: 'gui_client' } });
      setIsLoginView(true);
      setError('Signup successful! Please login.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Signup failed.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('engram_token');
    localStorage.removeItem('engram_eat');
    setIsAuthenticated(false);
  };

  const saveBaseUrl = () => {
    const nextUrl = baseUrlDraft.trim();
    if (!nextUrl) return;
    persistBaseUrl(nextUrl);
    setBaseUrl(nextUrl);
    setError(null);
  };

  const runTask = async () => {
    if (!taskInput.trim()) return;
    setIsExecuting(true);
    setError(null);
    try {
      const submission = await tasks.submit(taskInput, {
        client: 'engram-gui',
        timestamp: Date.now(),
      });
      const taskId = submission.task_id;
      addTaskToHistory({
        id: taskId,
        status: submission.status,
        message: submission.message,
        command: taskInput,
        submitted_at: new Date().toLocaleTimeString(),
      });
      void pollTask(taskId);
      setTaskInput('');
    } catch (err: any) {
      setError(err.message || 'Task submission failed.');
    } finally {
      setIsExecuting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="auth-container flex-center">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="auth-card glass glow"
        >
          <div className="auth-header">
            <pre className="ascii-logo">{`+--------------------------------------+
  E N G R A M :: ACCESS TERMINAL      +
--------------------------------------+
  NODE  : LOCALHOST
  ROUTE : /api/v1/auth/login
  MODE  : ${isLoginView ? 'LOGIN' : 'SIGNUP'}
--------------------------------------+`}</pre>
            <div className="auth-title">{isLoginView ? 'LOGIN' : 'SIGNUP'}</div>
            <p>{isLoginView ? 'Enter credentials to open a secure session.' : 'Create a new operator profile to proceed.'}</p>
          </div>

          <form onSubmit={isLoginView ? handleLogin : handleSignup}>
            <div className="input-group">
              <label><User size={16} /> Email Address</label>
              <input 
                type="email" 
                value={email} 
                onChange={e => setEmail(e.target.value)} 
                placeholder="name@company.com"
                required
              />
            </div>
            <div className="input-group">
              <label><Lock size={16} /> Password</label>
              <input 
                type="password" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                placeholder="********"
                required
              />
            </div>

            {error && (
              <motion.div 
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`auth-error ${error.includes('successful') ? 'success' : ''}`}
              >
                <AlertCircle size={16} /> {error}
              </motion.div>
            )}

            <button type="submit" className="primary-btn glow-orange">
              {isLoginView ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              {isLoginView ? "Don't have an account?" : "Already have an account?"}
              <button onClick={() => setIsLoginView(!isLoginView)}>
                {isLoginView ? 'Create one' : 'Sign in instead'}
              </button>
            </p>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'} glass`}>
        <div className="sidebar-header">
          <Shield color="var(--accent-orange)" size={24} />
          <span className="brand-name">ENGRAM</span>
          <button onClick={() => setIsSidebarOpen(false)} className="close-sidebar">
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          <NavItem 
            icon={<Zap size={20} />} 
            label="Orchestrate" 
            active={activeTab === 'orchestrate'} 
            onClick={() => setActiveTab('orchestrate')} 
          />
          <NavItem 
            icon={<Database size={20} />} 
            label="Agent Registry" 
            active={activeTab === 'agents'} 
            onClick={() => setActiveTab('agents')} 
          />
          <NavItem 
            icon={<History size={20} />} 
            label="Task History" 
            active={activeTab === 'history'} 
            onClick={() => setActiveTab('history')} 
          />
          <NavItem 
            icon={<Settings size={20} />} 
            label="Settings" 
            active={activeTab === 'settings'} 
            onClick={() => setActiveTab('settings')} 
          />
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="avatar">U</div>
            <div className="details">
              <span className="user-email">{email || 'User'}</span>
              <span className="user-plan">Pro Plan</span>
            </div>
          </div>
          <button onClick={handleLogout} className="logout-btn">
            <LogOut size={18} /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="content-header">
          {!isSidebarOpen && (
            <button onClick={() => setIsSidebarOpen(true)} className="open-sidebar">
              <Menu size={20} />
            </button>
          )}
          <div className="header-status">
            <span className="status-blink"></span>
            <span className="status-text">Relay Node Online (Berlin)</span>
          </div>
          <div className="header-actions">
            <button key="refresh-btn" onClick={() => { loadAgents(); loadRecentTasks(); }} title="Refresh Agents">
              <RefreshCw size={18} />
            </button>
            <button key="notify-btn" title="Notifications">
              <Activity size={18} />
            </button>
          </div>
        </header>

        <section className="content-inner">
          <AnimatePresence mode="wait">
            {activeTab === 'orchestrate' && (
              <motion.div 
                key="orchestrate"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="orchestrate-view"
              >
                <div className="history-scroller">
                  {taskHistory.length === 0 ? (
                    <div className="empty-state">
                      <Zap size={48} className="dim-icon" />
                      <h2>Ready for Orchestration</h2>
                      <p>Enter a complex task below. The Engram backend will orchestrate the workflow and return results.</p>
                      <div className="example-chips">
                        <button onClick={() => setTaskInput("Translate a meeting summary from Slack (A2A) to Notion (MCP)")}>Slack to Notion</button>
                        <button onClick={() => setTaskInput("Fetch prices from Binance and alert on Telegram")}>Market Watch</button>
                      </div>
                    </div>
                  ) : (
                    <div className="history-list">
                      {taskHistory.map((task, i) => (
                        <TaskCard key={i} task={task} />
                      ))}
                      <div ref={historyEndRef} />
                    </div>
                  )}
                </div>

                <div className="input-footer">
                  <div className="input-wrapper glass glow">
                    <textarea 
                      placeholder="Send a command to the Engram backend..." 
                      value={taskInput}
                      onChange={e => setTaskInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), runTask())}
                      rows={1}
                    />
                    <button 
                      className={`send-btn ${isExecuting ? 'loading' : ''}`}
                      onClick={runTask}
                      disabled={isExecuting || !taskInput.trim()}
                    >
                      {isExecuting ? <RefreshCw className="spin" size={20} /> : <Send size={20} />}
                    </button>
                  </div>
                  <p className="input-hint">Secure API | EAT-protected orchestration | Structured request</p>
                </div>
              </motion.div>
            )}

            {activeTab === 'agents' && (
              <motion.div 
                key="agents"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="agents-view"
              >
                <div className="view-header">
                  <h1>Agent Registry</h1>
                  <p>Displaying all discovered AI agents and their protocol capabilities.</p>
                </div>
                <div className="agent-grid">
                  {agents.map((agent) => (
                    <AgentCard key={agent.agent_id} agent={agent} />
                  ))}
                  {agents.length === 0 && <p className="dim-text">No agents discovered yet.</p>}
                </div>
              </motion.div>
            )}
            
            {activeTab === 'history' && (
               <motion.div 
                 key="history"
                 initial={{ opacity: 0, x: 20 }}
                 animate={{ opacity: 1, x: 0 }}
                 exit={{ opacity: 0, x: -20 }}
                 className="history-view"
               >
                 <div className="view-header">
                    <h1>Session History</h1>
                    <p>Audit trail of all task executions in this session.</p>
                 </div>
                 <div className="history-table glass">
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr>
                                <th>Task ID</th>
                                <th>Status</th>
                                <th>Time</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {taskHistory.map((t, i) => (
                                <tr key={i}>
                                    <td className="dim-text">{t.id}</td>
                                    <td><span className={`status-pill ${t.status}`}>{t.status}</span></td>
                                    <td>{t.updated_at || t.submitted_at || '-'}</td>
                                    <td><button className="text-btn">Details</button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                 </div>
               </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div 
                key="settings"
                initial={{ opacity: 0, filter: 'blur(5px)' }}
                animate={{ opacity: 1, filter: 'blur(0)' }}
                exit={{ opacity: 0 }}
                className="settings-view"
              >
                <div className="view-header">
                  <h1>Security & Access</h1>
                  <p>Manage your Engram Access Tokens (EAT) and security configuration.</p>
                </div>
                <div className="settings-card glass">
                  <div className="setting-row">
                    <div className="row-info">
                      <h3>Engram API Base URL</h3>
                      <p>Point the client at your Engram Identity Server and orchestration API.</p>
                      <div className="base-url-field">
                        <input
                          type="text"
                          value={baseUrlDraft}
                          onChange={e => setBaseUrlDraft(e.target.value)}
                          placeholder="http://localhost:8000/api/v1"
                        />
                        <span className="base-url-active">Active: {baseUrl}</span>
                      </div>
                    </div>
                    <button onClick={saveBaseUrl} className="secondary-btn">
                      <CheckCircle2 size={16} /> Save
                    </button>
                  </div>
                  <div className="setting-row">
                    <div className="row-info">
                      <h3>Engram Access Token (EAT)</h3>
                      <p>This token allows external agents to securely use the orchestration layer on your behalf.</p>
                      <div className="token-display">
                        <code>{eat ? `${eat.substring(0, 16)}...` : 'No token generated'}</code>
                      </div>
                    </div>
                    <button onClick={generateEat} className="secondary-btn">
                      <RefreshCw size={16} /> Regenerate
                    </button>
                  </div>
                  
                  <div className="setting-row">
                    <div className="row-info">
                      <h3>Protocol Delta Rules</h3>
                      <p>Manage how protocols are normalized before reaching agents.</p>
                    </div>
                    <button className="secondary-btn">Manage Rules</button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </main>
    </div>
  );
};

// Sub-components
const NavItem = ({ icon, label, active, onClick }: { icon: any, label: string, active: boolean, onClick: () => void }) => (
  <button className={`nav-item ${active ? 'active' : ''}`} onClick={onClick}>
    {icon}
    <span>{label}</span>
    {active && <motion.div layoutId="nav-bg" className="active-indicator" />}
  </button>
);

const AgentCard = ({ agent }: { agent: Agent }) => (
  <div className="agent-card glass">
    <div className="agent-card-header">
      <div className={`status-dot ${agent.is_active ? 'online' : 'offline'}`}></div>
      <h3>{agent.name || 'Anonymous Agent'}</h3>
    </div>
    <div className="agent-id">ID: {agent.agent_id.substring(0, 8)}...</div>
    <div className="protocols-tags">
      {agent.supported_protocols.map(p => (
        <span key={p} className="protocol-tag">{p}</span>
      ))}
    </div>
  </div>
);

const TaskCard = ({ task }: { task: TaskResult }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const statusIcon = task.status === 'COMPLETED'
    ? <CheckCircle2 color="var(--success)" size={20} />
    : task.status === 'DEAD_LETTER'
      ? <AlertCircle color="var(--error)" size={20} />
      : <Zap color="var(--accent-orange)" size={20} />;
  
  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="task-card-outer"
    >
      <div className="task-card glass">
        <div className="task-header" onClick={() => setIsExpanded(!isExpanded)}>
          <div className="task-status-icon">
            {statusIcon}
          </div>
          <div className="task-summary">
            <span className="task-id">Task: {task.id}</span>
            <span className="task-time">{task.updated_at || task.submitted_at || '-'}</span>
          </div>
          <div className="task-expand-btn">
             {isExpanded ? <ChevronRight size={18} style={{ transform: 'rotate(90deg)' }} /> : <ChevronRight size={18} />}
          </div>
        </div>
        
        <AnimatePresence>
          {isExpanded && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="task-details"
            >
              <div className="details-section">
                <h4>Command</h4>
                <pre>{task.command || 'Command not captured for this task.'}</pre>
              </div>
              
              <div className="details-section">
                <h4>Workflow Results</h4>
                <pre>{JSON.stringify(task.results || {}, null, 2)}</pre>
              </div>

              {task.last_error && (
                <div className="details-section">
                  <h4>Last Error</h4>
                  <pre>{task.last_error}</pre>
                </div>
              )}

              {task.results && Object.keys(task.results).length > 0 && (
                <div className="trace-section">
                  <h4>Agent Trace</h4>
                  <div className="trace-timeline">
                    {Object.entries(task.results).map(([id], i) => (
                      <div key={i} className="trace-step">
                        <Terminal size={14} />
                        <span className="agent-span">{id}</span>
                        <span className="agent-val">Result captured successfully.</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default App;


