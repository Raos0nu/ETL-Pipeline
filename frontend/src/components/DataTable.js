import React, { useState } from 'react';
import './DataTable.css';

function DataTable({ data, onDelete, onUpdate, onBulkDelete, fetchData }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState('order_id');
  const [sortDirection, setSortDirection] = useState('asc');
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(10);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredData = data.filter(item =>
    item.product.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.order_id.toString().includes(searchTerm)
  );

  const sortedData = [...filteredData].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    
    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  // Pagination
  const totalPages = Math.ceil(sortedData.length / perPage);
  const startIdx = (currentPage - 1) * perPage;
  const endIdx = startIdx + perPage;
  const paginatedData = sortedData.slice(startIdx, endIdx);

  const handleDelete = (orderId) => {
    if (window.confirm(`Are you sure you want to delete order #${orderId}?`)) {
      onDelete(orderId);
    }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedRows(new Set(paginatedData.map(item => item.order_id)));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleSelectRow = (orderId) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(orderId)) {
      newSelected.delete(orderId);
    } else {
      newSelected.add(orderId);
    }
    setSelectedRows(newSelected);
  };

  const handleBulkDelete = () => {
    if (selectedRows.size === 0) return;
    if (window.confirm(`Are you sure you want to delete ${selectedRows.size} selected record(s)?`)) {
      onBulkDelete(Array.from(selectedRows));
      setSelectedRows(new Set());
    }
  };

  const handleEdit = (row) => {
    setEditingRow(row.order_id);
    setEditForm({
      product: row.product,
      quantity: row.quantity,
      price: row.price
    });
  };

  const handleSaveEdit = async () => {
    const success = await onUpdate(editingRow, editForm);
    if (success) {
      setEditingRow(null);
      setEditForm({});
    }
  };

  const handleCancelEdit = () => {
    setEditingRow(null);
    setEditForm({});
  };

  return (
    <div className="data-table-container">
      <div className="table-header">
        <h2>📋 Sales Data Table</h2>
        <div className="table-controls">
          <input
            type="text"
            placeholder="🔍 Search by product or order ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <div className="table-actions">
            {selectedRows.size > 0 && (
              <button className="bulk-delete-btn" onClick={handleBulkDelete}>
                🗑️ Delete Selected ({selectedRows.size})
              </button>
            )}
            <span className="record-count">{sortedData.length} records</span>
          </div>
        </div>
      </div>

      <div className="pagination-controls-top">
        <div className="per-page-selector">
          <label>Show:</label>
          <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setCurrentPage(1); }}>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
        <div className="page-info">
          Page {currentPage} of {totalPages || 1}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={paginatedData.length > 0 && paginatedData.every(item => selectedRows.has(item.order_id))}
                  onChange={handleSelectAll}
                />
              </th>
              <th onClick={() => handleSort('order_id')} className="sortable">
                Order ID {sortField === 'order_id' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('product')} className="sortable">
                Product {sortField === 'product' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('quantity')} className="sortable">
                Quantity {sortField === 'quantity' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('price')} className="sortable">
                Price {sortField === 'price' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th onClick={() => handleSort('total_price')} className="sortable">
                Total {sortField === 'total_price' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((item, index) => (
              <tr key={index} className={selectedRows.has(item.order_id) ? 'selected' : ''}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedRows.has(item.order_id)}
                    onChange={() => handleSelectRow(item.order_id)}
                  />
                </td>
                <td className="order-id-cell">#{item.order_id}</td>
                <td className="product-cell">
                  {editingRow === item.order_id ? (
                    <input
                      type="text"
                      value={editForm.product}
                      onChange={(e) => setEditForm({...editForm, product: e.target.value})}
                      className="edit-input"
                    />
                  ) : (
                    item.product
                  )}
                </td>
                <td>
                  {editingRow === item.order_id ? (
                    <input
                      type="number"
                      value={editForm.quantity}
                      onChange={(e) => setEditForm({...editForm, quantity: e.target.value})}
                      className="edit-input"
                    />
                  ) : (
                    item.quantity
                  )}
                </td>
                <td>
                  {editingRow === item.order_id ? (
                    <input
                      type="number"
                      step="0.01"
                      value={editForm.price}
                      onChange={(e) => setEditForm({...editForm, price: e.target.value})}
                      className="edit-input"
                    />
                  ) : (
                    formatCurrency(item.price)
                  )}
                </td>
                <td className="total-cell">
                  {editingRow === item.order_id ? (
                    formatCurrency((parseFloat(editForm.quantity || 0) * parseFloat(editForm.price || 0)))
                  ) : (
                    formatCurrency(item.total_price)
                  )}
                </td>
                <td>
                  {editingRow === item.order_id ? (
                    <div className="edit-actions">
                      <button className="save-btn" onClick={handleSaveEdit}>✓</button>
                      <button className="cancel-btn" onClick={handleCancelEdit}>✕</button>
                    </div>
                  ) : (
                    <div className="row-actions">
                      <button 
                        className="edit-btn"
                        onClick={() => handleEdit(item)}
                        title="Edit order"
                      >
                        ✏️
                      </button>
                      <button 
                        className="delete-btn"
                        onClick={() => handleDelete(item.order_id)}
                        title="Delete order"
                      >
                        🗑️
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sortedData.length === 0 && (
        <div className="no-data">
          <p>No data found matching your search.</p>
        </div>
      )}

      {totalPages > 1 && (
        <div className="pagination-controls">
          <button 
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="page-btn"
          >
            ← Previous
          </button>
          <div className="page-numbers">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`page-btn ${currentPage === pageNum ? 'active' : ''}`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          <button 
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="page-btn"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

export default DataTable;
