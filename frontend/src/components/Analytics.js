import React, { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import './Analytics.css';
import { getProductAnalytics, getTimeseriesAnalytics } from '../services/api';

// ── Palette ───────────────────────────────────────────────────────────────────
const COLORS = ['#6366f1','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899'];

const fmtUSD   = (v) => `$${Number(v).toFixed(2)}`;
const fmtShort = (v) => {
  if (v >= 1_000_000) return `$${(v/1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `$${(v/1_000).toFixed(1)}K`;
  return `$${Number(v).toFixed(0)}`;
};

// ── Custom tooltip ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="tooltip-label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="tooltip-row">
          <span className="tooltip-dot" style={{ background: p.color }} />
          <span className="tooltip-name">{p.name}:</span>
          <span className="tooltip-val">
            {typeof p.value === 'number' && p.name?.toLowerCase().includes('revenue')
              ? fmtUSD(p.value) : p.value?.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
};

// ── Skeleton ──────────────────────────────────────────────────────────────────
const ChartSkeleton = () => (
  <div className="chart-skeleton">
    <div className="skeleton" style={{ height: 280 }} />
  </div>
);

// ── KPI strip ─────────────────────────────────────────────────────────────────
function KpiStrip({ products }) {
  if (!products?.length) return null;
  const topProduct   = products[0];
  const totalRev     = products.reduce((s, p) => s + (p.total_revenue || 0), 0);
  const totalUnits   = products.reduce((s, p) => s + (p.total_quantity || 0), 0);
  const avgOrderVal  = totalRev / (products.reduce((s, p) => s + (p.order_count || 0), 0) || 1);

  const kpis = [
    { label: 'Top Product',    value: topProduct?.product || '—',     accent: 'indigo' },
    { label: 'Total Revenue',  value: fmtShort(totalRev),             accent: 'emerald' },
    { label: 'Units Sold',     value: totalUnits.toLocaleString(),    accent: 'violet' },
    { label: 'Avg Order Value',value: fmtUSD(avgOrderVal),            accent: 'cyan' },
  ];

  return (
    <div className="kpi-strip">
      {kpis.map((k) => (
        <div key={k.label} className={`kpi-card kpi-${k.accent}`}>
          <div className="kpi-value">{k.value}</div>
          <div className="kpi-label">{k.label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function Analytics({ salesData }) {
  const [products,   setProducts]   = useState([]);
  const [timeseries, setTimeseries] = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pRes, tRes] = await Promise.allSettled([
        getProductAnalytics(),
        getTimeseriesAnalytics(),
      ]);
      if (pRes.status === 'fulfilled') setProducts(pRes.value.data?.data || []);
      if (tRes.status === 'fulfilled') setTimeseries(tRes.value.data?.data || []);
    } catch (e) {
      setError('Failed to load analytics data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load, salesData]);

  if (error) return (
    <div className="analytics-error card">
      <div className="error-icon">⚠</div>
      <p>{error}</p>
      <button className="btn btn-secondary" onClick={load}>Retry</button>
    </div>
  );

  return (
    <div className="analytics-page animate-slide-up">
      {/* Header */}
      <div className="section-header">
        <div>
          <h1 className="section-title">Analytics</h1>
          <p className="section-subtitle">
            Visualised insights across products, revenue, and time
          </p>
        </div>
        <button className="btn btn-secondary" onClick={load} style={{ fontSize: '.8rem' }}>
          ↺ Refresh
        </button>
      </div>

      {/* KPI strip */}
      {loading ? (
        <div className="kpi-strip">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 90, borderRadius: 14 }} />
          ))}
        </div>
      ) : (
        <KpiStrip products={products} />
      )}

      {/* Charts grid */}
      <div className="charts-grid">

        {/* Revenue over time — Area */}
        <div className="chart-card card full-width">
          <div className="chart-card-header">
            <div className="chart-title">Revenue Over Time</div>
            <span className="badge badge-info">{timeseries.length} data points</span>
          </div>
          {loading ? <ChartSkeleton /> : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={timeseries} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-base)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} />
                <YAxis tickFormatter={fmtShort} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2.5}
                      fill="url(#gradRev)" name="Revenue" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Orders over time — Line */}
        <div className="chart-card card">
          <div className="chart-card-header">
            <div className="chart-title">Orders Over Time</div>
          </div>
          {loading ? <ChartSkeleton /> : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={timeseries} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-base)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="orders" stroke="#10b981" strokeWidth={2.5}
                      dot={{ fill: '#10b981', r: 3 }} activeDot={{ r: 5 }} name="Orders" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Revenue by product — Bar */}
        <div className="chart-card card">
          <div className="chart-card-header">
            <div className="chart-title">Revenue by Product</div>
          </div>
          {loading ? <ChartSkeleton /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={products} margin={{ top: 8, right: 16, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-base)" />
                <XAxis dataKey="product" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                       tickLine={false} angle={-30} textAnchor="end" interval={0} />
                <YAxis tickFormatter={fmtShort} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                       axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="total_revenue" name="Revenue" radius={[6, 6, 0, 0]}>
                  {products.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Sales distribution — Pie */}
        <div className="chart-card card">
          <div className="chart-card-header">
            <div className="chart-title">Sales Distribution</div>
          </div>
          {loading ? <ChartSkeleton /> : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={products} dataKey="total_revenue" nameKey="product"
                     cx="50%" cy="45%" outerRadius={90} innerRadius={40}
                     paddingAngle={3}
                     label={({ name, percent }) =>
                       `${name} ${(percent * 100).toFixed(0)}%`}
                     labelLine={{ stroke: 'var(--text-muted)', strokeWidth: 1 }}>
                  {products.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => fmtUSD(v)} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Units sold — Bar */}
        <div className="chart-card card">
          <div className="chart-card-header">
            <div className="chart-title">Units Sold by Product</div>
          </div>
          {loading ? <ChartSkeleton /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={products} margin={{ top: 8, right: 16, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-base)" />
                <XAxis dataKey="product" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                       tickLine={false} angle={-30} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                       axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="total_quantity" name="Units" radius={[6, 6, 0, 0]}>
                  {products.map((_, i) => (
                    <Cell key={i} fill={COLORS[(i + 2) % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Avg price per product — Line */}
        <div className="chart-card card">
          <div className="chart-card-header">
            <div className="chart-title">Avg. Order Value by Product</div>
          </div>
          {loading ? <ChartSkeleton /> : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={products} margin={{ top: 8, right: 16, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-base)" />
                <XAxis dataKey="product" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                       tickLine={false} angle={-30} textAnchor="end" interval={0} />
                <YAxis tickFormatter={fmtShort} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                       axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="avg_order_value" name="Avg Order Value"
                      stroke="#f59e0b" strokeWidth={2.5}
                      dot={{ fill: '#f59e0b', r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

      </div>

      {/* Product performance table */}
      <div className="card perf-table-card">
        <div className="panel-header">
          <h3 className="panel-title">Product Performance Summary</h3>
          <span className="badge badge-info">{products.length} products</span>
        </div>
        {loading ? (
          <div className="skeleton" style={{ height: 200 }} />
        ) : products.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">◫</div>
            <p>No product data available. Run the ETL pipeline first.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="perf-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Product</th>
                  <th>Orders</th>
                  <th>Units Sold</th>
                  <th>Avg Price</th>
                  <th>Total Revenue</th>
                  <th>Avg Order</th>
                  <th>Share</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const totalRev = products.reduce((s, p) => s + (p.total_revenue || 0), 0);
                  return products.map((p, i) => {
                    const share = totalRev ? ((p.total_revenue / totalRev) * 100).toFixed(1) : '0.0';
                    return (
                      <tr key={i}>
                        <td className="rank-cell">
                          <span className="rank-badge" style={{ background: COLORS[i % COLORS.length] }}>
                            {i + 1}
                          </span>
                        </td>
                        <td className="product-name-cell">
                          <span className="color-dot" style={{ background: COLORS[i % COLORS.length] }} />
                          {p.product}
                        </td>
                        <td>{p.order_count?.toLocaleString()}</td>
                        <td>{p.total_quantity?.toLocaleString()}</td>
                        <td>{fmtUSD(p.avg_price || 0)}</td>
                        <td className="rev-cell">{fmtUSD(p.total_revenue)}</td>
                        <td>{fmtUSD(p.avg_order_value || 0)}</td>
                        <td>
                          <div className="share-cell">
                            <div className="share-bar-bg">
                              <div className="share-bar-fill"
                                   style={{ width: `${share}%`, background: COLORS[i % COLORS.length] }} />
                            </div>
                            <span className="share-pct">{share}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  });
                })()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
