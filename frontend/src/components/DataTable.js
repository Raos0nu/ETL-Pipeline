import React, { useState, useMemo, useRef, useEffect } from 'react';
import './DataTable.css';
import { exportCSV, importCSV } from '../services/api';
import { toast } from 'react-hot-toast';

const fmtUSD = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n ?? 0);

// ── Skeleton rows ─────────────────────────────────────────────────────────────
function SkeletonRows({ count = 8 }) {
  return [...Array(count)].map((_, i) => (
    <tr key={i} className="skeleton-row">
      {[...Array(7)].map((_, j) => (
        <td key={j}><div className="skeleton" style={{ height: 16, borderRadius: 6 }} /></td>
      ))}
    </tr>
  ));
}

// ── Inline edit cell ──────────────────────────────────────────────────────────
function EditCell({ type = 'text', value, onChange, placeholder }) {
  return (
    <input
      className="edit-inline"
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      step={type === 'number' ? '0.01' : undefined}
      autoFocus
    />
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function DataTable({ data, loading, onDelete, onUpdate, onBulkDelete, onRefresh }) {
  const [search,       setSearch]       = useState('');
  const [sortField,    setSortField]    = useState('order_id');
  const [sortDir,      setSortDir]      = useState('asc');
  const [selected,     setSelected]     = useState(new Set());
  const [editingId,    setEditingId]    = useState(null);
  const [editForm,     setEditForm]     = useState({});
  const [page,         setPage]         = useState(1);
  const [perPage,      setPerPage]      = useState(10);
  const [importing,    setImporting]    = useState(false);
  const fileInputRef = useRef(null);

  // Reset page on data change
  const prevLenRef = useRef(data.length);
  useEffect(() => {
    if (data.length !== prevLenRef.current) {
      setPage(1);
      prevLenRef.current = data.length;
    }
  }, [data.length]);

  // ── Filter + sort ──────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return data.filter(r =>
      !q ||
      String(r.order_id).includes(q) ||
      (r.product || '').toLowerCase().includes(q)
    );
  }, [data, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let av = a[sortField], bv = b[sortField];
      if (typeof av === 'string') { av = av.toLowerCase(); bv = bv.toLowerCase(); }
      if (av === bv) return 0;
      const cmp = av > bv ? 1 : -1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / perPage));
  const paginated  = sorted.slice((page - 1) * perPage, page * perPage);

  const toggleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const sortIcon = (field) =>
    sortField !== field ? '⇅' : sortDir === 'asc' ? '↑' : '↓';

  // ── Selection ──────────────────────────────────────────────────────────────
  const toggleAll = (e) => {
    setSelected(e.target.checked ? new Set(paginated.map(r => r.order_id)) : new Set());
  };
  const toggleRow = (id) => {
    setSelected(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  // ── Edit ───────────────────────────────────────────────────────────────────
  const startEdit = (row) => {
    setEditingId(row.order_id);
    setEditForm({ product: row.product, quantity: row.quantity, price: row.price });
  };

  const saveEdit = async () => {
    const ok = await onUpdate(editingId, {
      product:  editForm.product,
      quantity: Number(editForm.quantity),
      price:    Number(editForm.price),
    });
    if (ok) { setEditingId(null); setEditForm({}); }
  };

  // ── Delete ─────────────────────────────────────────────────────────────────
  const confirmDelete = (id) => {
    if (window.confirm(`Delete order #${id}? This cannot be undone.`)) onDelete(id);
  };

  const confirmBulkDelete = () => {
    if (!selected.size) return;
    if (window.confirm(`Delete ${selected.size} selected record(s)?`)) {
      onBulkDelete(Array.from(selected));
      setSelected(new Set());
    }
  };

  // ── CSV import ─────────────────────────────────────────────────────────────
  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    const tid = toast.loading(`Importing ${file.name}…`);
    try {
      const res = await importCSV(file);
      if (res.data.success) {
        toast.success(res.data.message || 'Import successful', { id: tid });
        onRefresh?.();
      }
    } catch (err) {
      toast.error(err.message || 'Import failed', { id: tid });
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  };

  // ── Pagination buttons ─────────────────────────────────────────────────────
  const pageButtons = useMemo(() => {
    const btns = [];
    const delta = 2;
    const lo = Math.max(1, page - delta);
    const hi = Math.min(totalPages, page + delta);
    if (lo > 1) { btns.push(1); if (lo > 2) btns.push('…'); }
    for (let i = lo; i <= hi; i++) btns.push(i);
    if (hi < totalPages) { if (hi < totalPages - 1) btns.push('…'); btns.push(totalPages); }
    return btns;
  }, [page, totalPages]);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="datatable-page animate-slide-up">
      {/* Header */}
      <div className="section-header">
        <div>
          <h1 className="section-title">Data Table</h1>
          <p className="section-subtitle">
            {sorted.length.toLocaleString()} record{sorted.length !== 1 ? 's' : ''}
            {search ? ` matching "${search}"` : ''}
          </p>
        </div>
        <div className="dt-toolbar">
          {selected.size > 0 && (
            <button className="btn btn-danger" onClick={confirmBulkDelete}>
              🗑 Delete ({selected.size})
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => exportCSV()} title="Export all as CSV">
            ↓ Export CSV
          </button>
          <label className={`btn btn-secondary ${importing ? 'loading' : ''}`} title="Import CSV">
            {importing ? <><span className="spinner-sm" /> Importing…</> : '↑ Import CSV'}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              onChange={handleImport}
            />
          </label>
          <button className="btn btn-secondary" onClick={onRefresh} title="Refresh data">
            ↺
          </button>
        </div>
      </div>

      {/* Controls bar */}
      <div className="dt-controls card">
        <input
          className="input dt-search"
          type="text"
          placeholder="Search by product or order ID…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <div className="dt-per-page">
          <label className="per-page-label">Show</label>
          <select
            className="input per-page-select"
            value={perPage}
            onChange={(e) => { setPerPage(+e.target.value); setPage(1); }}
          >
            {[10, 25, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <span className="per-page-label">per page</span>
        </div>
      </div>

      {/* Table */}
      <div className="card dt-card">
        <div className="table-scroll">
          <table className="dt-table">
            <thead>
              <tr>
                <th className="check-col">
                  <input
                    type="checkbox"
                    checked={paginated.length > 0 && paginated.every(r => selected.has(r.order_id))}
                    onChange={toggleAll}
                  />
                </th>
                {[
                  { key: 'order_id',    label: 'Order ID'  },
                  { key: 'product',     label: 'Product'   },
                  { key: 'quantity',    label: 'Qty'       },
                  { key: 'price',       label: 'Unit Price'},
                  { key: 'total_price', label: 'Total'     },
                ].map(col => (
                  <th key={col.key} className="sortable" onClick={() => toggleSort(col.key)}>
                    {col.label}
                    <span className="sort-icon">{sortIcon(col.key)}</span>
                  </th>
                ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <SkeletonRows />
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <div className="empty-icon">◫</div>
                      <p>{search ? `No records match "${search}".` : 'No data found. Add records or run the ETL pipeline.'}</p>
                    </div>
                  </td>
                </tr>
              ) : (
                paginated.map(row => {
                  const isEditing = editingId === row.order_id;
                  const isSelected = selected.has(row.order_id);
                  return (
                    <tr key={row.order_id} className={`${isSelected ? 'row-selected' : ''} ${isEditing ? 'row-editing' : ''}`}>
                      <td className="check-col">
                        <input type="checkbox" checked={isSelected} onChange={() => toggleRow(row.order_id)} />
                      </td>
                      <td className="id-cell">
                        <span className="order-pill">#{row.order_id}</span>
                      </td>
                      <td className="product-col">
                        {isEditing
                          ? <EditCell value={editForm.product} onChange={v => setEditForm(f => ({ ...f, product: v }))} placeholder="Product name" />
                          : <span className="product-name">{row.product}</span>}
                      </td>
                      <td>
                        {isEditing
                          ? <EditCell type="number" value={editForm.quantity} onChange={v => setEditForm(f => ({ ...f, quantity: v }))} />
                          : row.quantity?.toLocaleString()}
                      </td>
                      <td>
                        {isEditing
                          ? <EditCell type="number" value={editForm.price} onChange={v => setEditForm(f => ({ ...f, price: v }))} />
                          : fmtUSD(row.price)}
                      </td>
                      <td className="total-col">
                        {isEditing
                          ? <span className="preview-total">{fmtUSD((+editForm.quantity || 0) * (+editForm.price || 0))}</span>
                          : <strong>{fmtUSD(row.total_price)}</strong>}
                      </td>
                      <td>
                        <div className="row-actions">
                          {isEditing ? (
                            <>
                              <button className="action-btn save-btn" onClick={saveEdit} title="Save">✓</button>
                              <button className="action-btn cancel-btn" onClick={() => setEditingId(null)} title="Cancel">✕</button>
                            </>
                          ) : (
                            <>
                              <button className="action-btn edit-btn" onClick={() => startEdit(row)} title="Edit">✎</button>
                              <button className="action-btn delete-btn" onClick={() => confirmDelete(row.order_id)} title="Delete">🗑</button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="dt-pagination">
            <span className="page-info">
              Page {page} of {totalPages}
            </span>
            <div className="page-btns">
              <button className="page-btn" onClick={() => setPage(1)} disabled={page === 1}>«</button>
              <button className="page-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>‹</button>
              {pageButtons.map((b, i) =>
                b === '…'
                  ? <span key={`ellipsis-${i}`} className="page-ellipsis">…</span>
                  : <button key={b} className={`page-btn ${page === b ? 'active' : ''}`} onClick={() => setPage(b)}>{b}</button>
              )}
              <button className="page-btn" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>›</button>
              <button className="page-btn" onClick={() => setPage(totalPages)} disabled={page === totalPages}>»</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
