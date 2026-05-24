import React, { useState, useEffect, useCallback } from 'react';
import './Pipeline.css';
import { runETL, getJobHistory, getStatus, getAnalyticsOverview } from '../services/api';
import { toast } from 'react-hot-toast';

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmtDuration = (s) => {
  if (!s && s !== 0) return '—';
  if (s < 1)   return `${Math.round(s * 1000)}ms`;
  if (s < 60)  return `${s.toFixed(2)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
};

const fmtTime = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return iso; }
};

const statusColor = (s) => {
  switch (s) {
    case 'completed': return 'success';
    case 'failed':    return 'danger';
    case 'running':   return 'info';
    case 'queued':    return 'warning';
    default:          return 'info';
  }
};

// ── Step indicator ────────────────────────────────────────────────────────────
function PipelineSteps({ activeStep }) {
  const steps = [
    { id: 'extract',   label: 'Extract',   icon: '↓', desc: 'Read source data' },
    { id: 'transform', label: 'Transform', icon: '⟳', desc: 'Validate & enrich' },
    { id: 'load',      label: 'Load',      icon: '↑', desc: 'Persist to database' },
  ];
  return (
    <div className="pipeline-steps">
      {steps.map((step, i) => (
        <React.Fragment key={step.id}>
          <div className={`step ${activeStep === step.id ? 'active' : activeStep === 'done' || i < steps.findIndex(s => s.id === activeStep) ? 'done' : ''}`}>
            <div className="step-circle">
              {activeStep === step.id ? (
                <span className="step-spinner" />
              ) : (
                <span>{step.icon}</span>
              )}
            </div>
            <div className="step-info">
              <div className="step-label">{step.label}</div>
              <div className="step-desc">{step.desc}</div>
            </div>
          </div>
          {i < steps.length - 1 && (
            <div className={`step-connector ${activeStep === 'done' || i < steps.findIndex(s => s.id === activeStep) ? 'filled' : ''}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ── Job row ───────────────────────────────────────────────────────────────────
function JobRow({ job }) {
  const [expanded, setExpanded] = useState(false);
  const sc = statusColor(job.status);

  return (
    <>
      <tr className={`job-row ${expanded ? 'expanded' : ''}`} onClick={() => setExpanded(e => !e)}>
        <td>
          <span className={`status-chip status-${sc}`}>
            <span className="chip-dot" />
            {job.status}
          </span>
        </td>
        <td className="job-id-cell" title={job.id || job.job_id}>
          {(job.id || job.job_id || '').slice(0, 22)}…
        </td>
        <td>{fmtTime(job.started_at)}</td>
        <td>{fmtDuration(job.duration_seconds)}</td>
        <td>
          {job.records_loaded != null
            ? <span className="num-pill">{job.records_loaded?.toLocaleString()}</span>
            : '—'}
        </td>
        <td>
          {job.quality_score != null
            ? <span className={`quality-chip ${job.quality_score >= .95 ? 'good' : job.quality_score >= .8 ? 'ok' : 'bad'}`}>
                {(job.quality_score * 100).toFixed(1)}%
              </span>
            : '—'}
        </td>
        <td>
          <span className="trigger-tag">{job.triggered_by || 'manual'}</span>
        </td>
        <td><span className="expand-btn">{expanded ? '▲' : '▼'}</span></td>
      </tr>
      {expanded && (
        <tr className="job-detail-row">
          <td colSpan={8}>
            <div className="job-detail">
              {job.error_message && (
                <div className="detail-error">
                  <span>✕</span> {job.error_message}
                </div>
              )}
              <div className="detail-grid">
                {[
                  ['Extracted',   job.records_extracted],
                  ['Transformed', job.records_transformed],
                  ['Valid',        job.records_valid],
                  ['Invalid',      job.records_invalid],
                  ['Loaded',       job.records_loaded],
                ].map(([k, v]) => v != null && (
                  <div key={k} className="detail-item">
                    <span className="detail-key">{k}</span>
                    <span className="detail-val">{v?.toLocaleString() ?? '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Main Pipeline component ───────────────────────────────────────────────────
export default function Pipeline({ onDataRefresh }) {
  const [jobs,       setJobs]       = useState([]);
  const [overview,   setOverview]   = useState(null);
  const [status,     setStatus]     = useState(null);
  const [running,    setRunning]    = useState(false);
  const [activeStep, setActiveStep] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [mode,       setMode]       = useState('sync');
  const [histLoading,setHistLoad]   = useState(true);

  // ── Fetch history ─────────────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    try {
      const [histRes, statusRes, ovRes] = await Promise.allSettled([
        getJobHistory(20),
        getStatus(),
        getAnalyticsOverview(),
      ]);
      if (histRes.status === 'fulfilled')   setJobs(histRes.value.data?.data || []);
      if (statusRes.status === 'fulfilled') setStatus(statusRes.value.data?.data);
      if (ovRes.status === 'fulfilled')     setOverview(ovRes.value.data?.data);
    } catch { /* silent */ }
    finally { setHistLoad(false); }
  }, []);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  // ── Run pipeline ──────────────────────────────────────────────────────────
  const handleRun = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setLastResult(null);
    setActiveStep('extract');

    const stepTimings = [
      () => setActiveStep('extract'),
      () => setActiveStep('transform'),
      () => setActiveStep('load'),
    ];
    let stepIdx = 1;
    const stepTimer = setInterval(() => {
      if (stepIdx < stepTimings.length) {
        stepTimings[stepIdx](); stepIdx++;
      }
    }, 700);

    const tid = toast.loading('Pipeline executing…');
    try {
      const res = await runETL(mode, 'pipeline-page');
      clearInterval(stepTimer);

      if (res.data.success) {
        setActiveStep('done');
        const d = res.data.data || {};
        setLastResult(d);
        toast.success(
          `Pipeline done — ${d.records_loaded ?? 0} records loaded  (${fmtDuration(d.duration_seconds)})`,
          { id: tid, duration: 5000 }
        );
        onDataRefresh?.();
        fetchHistory();
      }
    } catch (e) {
      clearInterval(stepTimer);
      setActiveStep(null);
      toast.error(e.message || 'Pipeline failed', { id: tid });
    } finally {
      setRunning(false);
      setTimeout(() => setActiveStep(null), 2500);
    }
  }, [running, mode, onDataRefresh, fetchHistory]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="pipeline-page animate-slide-up">
      <div className="section-header">
        <div>
          <h1 className="section-title">Pipeline Monitor</h1>
          <p className="section-subtitle">
            Execute, monitor, and audit your ETL jobs in real time
          </p>
        </div>
        <button
          className={`btn btn-primary ${running ? 'loading' : ''}`}
          onClick={handleRun}
          disabled={running}
        >
          {running
            ? <><span className="spinner" /> Executing…</>
            : <><span>⚡</span> Run Now</>
          }
        </button>
      </div>

      {/* ── Top row: step vis + controls ─── */}
      <div className="pipeline-top-row">
        <div className="card pipeline-vis-card">
          <div className="card-label">Pipeline Flow</div>
          <PipelineSteps activeStep={activeStep} />
          {lastResult && (
            <div className="last-result-bar">
              <span>Last run: <strong>{lastResult.records_loaded}</strong> loaded</span>
              <span>Quality: <strong>{((lastResult.quality_score ?? 0) * 100).toFixed(1)}%</strong></span>
              <span>Duration: <strong>{fmtDuration(lastResult.duration_seconds)}</strong></span>
            </div>
          )}
        </div>

        <div className="card pipeline-controls-card">
          <div className="card-label">Execution Mode</div>
          <div className="mode-selector">
            {[
              { id: 'sync',  label: 'Synchronous', icon: '↺',
                desc: 'Wait for completion — result returned immediately' },
              { id: 'async', label: 'Async (Background)', icon: '⟳',
                desc: 'Fire-and-forget — runs in a background thread' },
            ].map(m => (
              <button
                key={m.id}
                className={`mode-btn ${mode === m.id ? 'active' : ''}`}
                onClick={() => setMode(m.id)}
              >
                <span className="mode-icon">{m.icon}</span>
                <div>
                  <div className="mode-label">{m.label}</div>
                  <div className="mode-desc">{m.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* System status */}
        {status && (
          <div className="card pipeline-status-card">
            <div className="card-label">System Status</div>
            <div className="sys-status-row">
              <span className="status-dot healthy" />
              <span className="sys-label">API</span>
              <span className="badge badge-success">Healthy</span>
            </div>
            {status.data_file && (
              <div className="sys-info-row">
                <span className="sys-info-key">Data file</span>
                <span className="sys-info-val">{status.data_file.name}</span>
              </div>
            )}
            {overview && (
              <>
                <div className="sys-info-row">
                  <span className="sys-info-key">Total records</span>
                  <span className="sys-info-val">{overview.total_orders?.toLocaleString()}</span>
                </div>
                <div className="sys-info-row">
                  <span className="sys-info-key">Quality score</span>
                  <span className="sys-info-val">
                    {((overview.quality_report?.quality_percentage ?? 0))}%
                  </span>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* ── Job history table ─── */}
      <div className="card job-history-card">
        <div className="panel-header">
          <h3 className="panel-title">Job History</h3>
          <button className="btn btn-secondary" onClick={fetchHistory} style={{ fontSize: '.8rem', padding: '6px 14px' }}>
            ↺ Refresh
          </button>
        </div>

        {histLoading ? (
          <div className="history-skeleton">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 44, marginBottom: 8 }} />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⟡</div>
            <p>No pipeline runs yet. Hit "Run Now" to execute your first job.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="job-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Job ID</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Records</th>
                  <th>Quality</th>
                  <th>Trigger</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job, i) => <JobRow key={job.id || job.job_id || i} job={job} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
