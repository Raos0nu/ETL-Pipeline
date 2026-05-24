import React, { useState, useEffect, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import './App.css';
import Dashboard    from './components/Dashboard';
import DataTable    from './components/DataTable';
import AddDataForm  from './components/AddDataForm';
import Analytics    from './components/Analytics';
import Pipeline     from './components/Pipeline';
import {
  getData, createRecord, updateRecord, deleteRecord,
  bulkDeleteRecords, runETL,
} from './services/api';

// ── Navigation tabs ──────────────────────────────────────────────────────────
const TABS = [
  { id: 'dashboard', label: 'Dashboard',     icon: '◈' },
  { id: 'pipeline',  label: 'Pipeline',      icon: '⚡' },
  { id: 'data',      label: 'Data Table',    icon: '⊞'  },
  { id: 'add',       label: 'Add Record',    icon: '+'  },
  { id: 'analytics', label: 'Analytics',     icon: '∿'  },
];

export default function App() {
  const [salesData,  setSalesData]  = useState([]);
  const [stats,      setStats]      = useState(null);
  const [quality,    setQuality]    = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [activeTab,  setActiveTab]  = useState('dashboard');
  const [darkMode,   setDarkMode]   = useState(
    () => localStorage.getItem('df-dark') === 'true'
  );
  const [etlRunning, setEtlRunning] = useState(false);

  // ── Dark mode sync ──────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.classList.toggle('dark-mode', darkMode);
    localStorage.setItem('df-dark', darkMode);
  }, [darkMode]);

  // ── Fetch data ───────────────────────────────────────────────────────────
  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await getData({ page: 1, per_page: 10000 });
      if (res.data.success) {
        setSalesData(res.data.data     || []);
        setStats(res.data.stats        || null);
        setQuality(res.data.quality_report || null);
      }
    } catch (e) {
      if (!silent) toast.error(e.message || 'Failed to fetch data');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── CRUD handlers ────────────────────────────────────────────────────────
  const handleAdd = useCallback(async (payload) => {
    try {
      const res = await createRecord(payload);
      if (res.data.success) {
        toast.success(res.data.message || 'Record created!');
        fetchData(true);
        return true;
      }
    } catch (e) {
      toast.error(e.message || 'Failed to create record');
    }
    return false;
  }, [fetchData]);

  const handleUpdate = useCallback(async (orderId, payload) => {
    try {
      const res = await updateRecord(orderId, payload);
      if (res.data.success) {
        toast.success(res.data.message || 'Record updated!');
        fetchData(true);
        return true;
      }
    } catch (e) {
      toast.error(e.message || 'Failed to update record');
    }
    return false;
  }, [fetchData]);

  const handleDelete = useCallback(async (orderId) => {
    try {
      const res = await deleteRecord(orderId);
      if (res.data.success) {
        toast.success(res.data.message || 'Record deleted');
        fetchData(true);
      }
    } catch (e) {
      toast.error(e.message || 'Failed to delete record');
    }
  }, [fetchData]);

  const handleBulkDelete = useCallback(async (orderIds) => {
    try {
      const res = await bulkDeleteRecords(orderIds);
      if (res.data.success) {
        toast.success(res.data.message || `${orderIds.length} records deleted`);
        fetchData(true);
      }
    } catch (e) {
      toast.error(e.message || 'Bulk delete failed');
    }
  }, [fetchData]);

  // ── ETL trigger ──────────────────────────────────────────────────────────
  const handleRunETL = useCallback(async () => {
    setEtlRunning(true);
    const tid = toast.loading('Running ETL pipeline…');
    try {
      const res = await runETL('sync', 'header-button');
      if (res.data.success) {
        const d = res.data.data || {};
        toast.success(
          `Pipeline complete — ${d.records_loaded ?? d.records_processed ?? '?'} records loaded`,
          { id: tid, duration: 4000 }
        );
        fetchData(true);
      }
    } catch (e) {
      toast.error(e.message || 'ETL pipeline failed', { id: tid });
    } finally {
      setEtlRunning(false);
    }
  }, [fetchData]);

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* Gradient mesh background */}
      <div className="app-bg" aria-hidden="true" />

      {/* ── HEADER ── */}
      <header className="app-header glass">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-logo">
              <span className="brand-icon">⟡</span>
            </div>
            <div className="brand-text">
              <span className="brand-name">DataFlow</span>
              <span className="brand-tag">Studio</span>
            </div>
            <span className="brand-version">v2.0</span>
          </div>

          <nav className="tab-nav" role="navigation" aria-label="Main navigation">
            {TABS.map(t => (
              <button
                key={t.id}
                className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
                onClick={() => setActiveTab(t.id)}
                aria-current={activeTab === t.id ? 'page' : undefined}
              >
                <span className="tab-icon">{t.icon}</span>
                <span className="tab-label">{t.label}</span>
              </button>
            ))}
          </nav>

          <div className="header-actions">
            {quality && (
              <div
                className={`quality-badge ${
                  quality.quality_percentage >= 95 ? 'badge-success' :
                  quality.quality_percentage >= 80 ? 'badge-warning' : 'badge-danger'
                } badge`}
                title={`Data quality score: ${quality.quality_percentage}%`}
              >
                ◎ {quality.quality_percentage}%
              </div>
            )}
            <button
              className={`btn-etl ${etlRunning ? 'loading' : ''}`}
              onClick={handleRunETL}
              disabled={etlRunning}
              title="Run ETL pipeline"
            >
              {etlRunning
                ? <><span className="spinner" /> Processing…</>
                : <><span>⚡</span> Run Pipeline</>
              }
            </button>
            <button
              className="btn-icon"
              onClick={() => setDarkMode(d => !d)}
              title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label="Toggle dark mode"
            >
              {darkMode ? '☀' : '◑'}
            </button>
          </div>
        </div>
      </header>

      {/* ── MAIN ── */}
      <main className="app-main">
        {loading && (
          <div className="page-loader">
            <div className="loader-bar" />
          </div>
        )}

        <div className="page-content animate-fade-in" key={activeTab}>
          {activeTab === 'dashboard' && (
            <Dashboard
              stats={stats}
              quality={quality}
              salesData={salesData}
              onRunETL={handleRunETL}
              etlRunning={etlRunning}
            />
          )}
          {activeTab === 'pipeline' && (
            <Pipeline onDataRefresh={() => fetchData(true)} />
          )}
          {activeTab === 'data' && (
            <DataTable
              data={salesData}
              loading={loading}
              onDelete={handleDelete}
              onUpdate={handleUpdate}
              onBulkDelete={handleBulkDelete}
              onRefresh={() => fetchData()}
            />
          )}
          {activeTab === 'add' && (
            <AddDataForm onAdd={handleAdd} />
          )}
          {activeTab === 'analytics' && (
            <Analytics salesData={salesData} />
          )}
        </div>
      </main>

      {/* ── FOOTER ── */}
      <footer className="app-footer">
        <span>© 2025 DataFlow Studio</span>
        <span className="footer-sep">·</span>
        <span>Real-Time ETL Pipeline & Analytics</span>
        <span className="footer-sep">·</span>
        <span>Built with React &amp; Flask</span>
      </footer>

      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            borderRadius: '12px',
            background: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-base)',
            boxShadow: 'var(--shadow-lg)',
            fontFamily: 'Inter, sans-serif',
            fontSize: '14px',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: '#fff' } },
          duration: 3500,
        }}
      />
    </div>
  );
}
