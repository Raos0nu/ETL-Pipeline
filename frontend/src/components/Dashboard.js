import React, { useMemo } from 'react';
import './Dashboard.css';

const fmt = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);

const fmtFull = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

function StatCard({ icon, label, value, sub, accent, trend }) {
  return (
    <div className={`stat-card stat-${accent}`}>
      <div className="stat-card-top">
        <span className="stat-icon">{icon}</span>
        {trend !== undefined && (
          <span className={`stat-trend ${trend >= 0 ? 'up' : 'down'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
      <div className="stat-card-glow" aria-hidden="true" />
    </div>
  );
}

function QualityMeter({ quality }) {
  if (!quality) return null;
  const pct = quality.quality_percentage ?? 0;
  const level = pct >= 95 ? 'excellent' : pct >= 80 ? 'good' : 'poor';
  const color = pct >= 95 ? '#10b981' : pct >= 80 ? '#f59e0b' : '#ef4444';
  const label = pct >= 95 ? 'Excellent' : pct >= 80 ? 'Good' : 'Needs Attention';

  return (
    <div className="quality-card card">
      <div className="quality-header">
        <div>
          <div className="quality-title">Data Quality</div>
          <div className="quality-subtitle">{quality.valid_rows} valid of {quality.total_rows} total rows</div>
        </div>
        <span className={`badge badge-${level === 'excellent' ? 'success' : level === 'good' ? 'warning' : 'danger'}`}>
          {label}
        </span>
      </div>
      <div className="quality-bar-wrap">
        <div className="quality-bar-bg">
          <div
            className="quality-bar-fill"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
        <span className="quality-pct">{pct}%</span>
      </div>
      {quality.issues?.length > 0 && (
        <div className="quality-issues">
          {quality.issues.slice(0, 3).map((issue, i) => (
            <div key={i} className="quality-issue">
              <span className="issue-dot" /> {issue}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecentOrders({ orders }) {
  if (!orders?.length) return (
    <div className="empty-state">
      <div className="empty-icon">◫</div>
      <p>No orders yet. Add data or run the ETL pipeline.</p>
    </div>
  );

  return (
    <div className="recent-list">
      {orders.map((o, i) => (
        <div key={i} className="recent-item">
          <div className="recent-badge" style={{ background: `hsl(${(o.order_id * 67) % 360},65%,55%)` }}>
            {(o.product || 'P').charAt(0).toUpperCase()}
          </div>
          <div className="recent-info">
            <div className="recent-product">{o.product}</div>
            <div className="recent-meta">Order #{o.order_id} · {o.quantity} units</div>
          </div>
          <div className="recent-revenue">{fmtFull(o.total_price)}</div>
        </div>
      ))}
    </div>
  );
}

function TopProducts({ data }) {
  if (!data?.length) return null;
  const top        = data.slice(0, 5);
  const getRevenue = (d) => d.total_revenue ?? d.total_price ?? 0;

  return (
    <div className="top-products">
      {top.map((p, i) => {
        const rev = getRevenue(p);
        const pct = (rev / (getRevenue(top[0]) || 1)) * 100;
        return (
          <div key={i} className="top-product-row">
            <span className="rank">#{i + 1}</span>
            <span className="tp-name">{p.product}</span>
            <div className="tp-bar-wrap">
              <div className="tp-bar" style={{ width: `${pct}%` }} />
            </div>
            <span className="tp-rev">{fmt(rev)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function Dashboard({ stats, quality, salesData, onRunETL, etlRunning }) {
  const recentOrders = useMemo(
    () => [...(salesData || [])].reverse().slice(0, 6),
    [salesData]
  );

  const topByRevenue = useMemo(() => {
    if (!salesData?.length) return [];
    const map = {};
    salesData.forEach(r => {
      if (!map[r.product]) map[r.product] = { product: r.product, total_revenue: 0 };
      map[r.product].total_revenue += (r.total_price ?? 0);
    });
    return Object.values(map).sort((a, b) => b.total_revenue - a.total_revenue);
  }, [salesData]);

  if (!stats) {
    return (
      <div className="dashboard-skeleton">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 130, borderRadius: 18 }} />
        ))}
      </div>
    );
  }

  return (
    <div className="dashboard animate-slide-up">
      {/* Page title */}
      <div className="section-header">
        <div>
          <h1 className="section-title">Overview</h1>
          <p className="section-subtitle">Real-time snapshot of your sales data pipeline</p>
        </div>
        {!etlRunning && (
          <button className="btn btn-primary" onClick={onRunETL}>
            ⚡ Run Pipeline
          </button>
        )}
      </div>

      {/* Stat cards */}
      <div className="stats-grid">
        <StatCard
          icon="◫" label="Total Orders"
          value={stats.total_orders?.toLocaleString() ?? '—'}
          sub="All processed records"
          accent="indigo"
        />
        <StatCard
          icon="$" label="Total Revenue"
          value={fmt(stats.total_revenue ?? 0)}
          sub="Cumulative sales value"
          accent="emerald"
        />
        <StatCard
          icon="~" label="Avg. Order Value"
          value={fmtFull(stats.average_order_value ?? 0)}
          sub="Per transaction"
          accent="violet"
        />
        <StatCard
          icon="⊞" label="Items Sold"
          value={(stats.total_items_sold ?? 0).toLocaleString()}
          sub="Total units dispatched"
          accent="cyan"
        />
        <StatCard
          icon="*" label="Products"
          value={stats.unique_products ?? '—'}
          sub="Distinct SKUs"
          accent="amber"
        />
        <StatCard
          icon="↑" label="Highest Order"
          value={fmtFull(stats.highest_value_order ?? 0)}
          sub="Single transaction peak"
          accent="rose"
        />
      </div>

      {/* Lower row */}
      <div className="dashboard-grid">
        {/* Quality meter */}
        <QualityMeter quality={quality} />

        {/* Top products */}
        <div className="card dashboard-panel">
          <div className="panel-header">
            <h3 className="panel-title">Top Products by Revenue</h3>
            <span className="panel-badge badge badge-info">{topByRevenue.length} SKUs</span>
          </div>
          <TopProducts data={topByRevenue} />
        </div>

        {/* Recent orders */}
        <div className="card dashboard-panel full-width">
          <div className="panel-header">
            <h3 className="panel-title">Recent Orders</h3>
            <span className="panel-badge badge badge-info">{salesData?.length ?? 0} total</span>
          </div>
          <RecentOrders orders={recentOrders} />
        </div>
      </div>
    </div>
  );
}
