import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import DataTable from './components/DataTable';
import AddDataForm from './components/AddDataForm';
import Analytics from './components/Analytics';
import axios from 'axios';
import toast from 'react-hot-toast';

function App() {
  const [salesData, setSalesData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [darkMode, setDarkMode] = useState(localStorage.getItem('darkMode') === 'true');

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark-mode');
    } else {
      document.documentElement.classList.remove('dark-mode');
    }
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  const fetchData = useCallback(async (page = 1, perPage = 50) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/data?page=${page}&per_page=${perPage}`);
      if (response.data.success) {
        setSalesData(response.data.data);
        setStats(response.data.stats);
        return response.data.pagination;
      }
    } catch (error) {
      toast.error('Error fetching data: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddData = async (newData) => {
    try {
      const response = await axios.post('/api/data', newData);
      if (response.data.success) {
        toast.success('Data added successfully!');
        fetchData();
        return true;
      }
    } catch (error) {
      toast.error('Error adding data: ' + error.message);
      return false;
    }
  };

  const handleUpdateData = async (orderId, updatedData) => {
    try {
      const response = await axios.put(`/api/data/${orderId}`, updatedData);
      if (response.data.success) {
        toast.success('Data updated successfully!');
        fetchData();
        return true;
      }
    } catch (error) {
      toast.error('Error updating data: ' + error.message);
      return false;
    }
  };

  const handleDeleteData = async (orderId) => {
    try {
      const response = await axios.delete(`/api/data/${orderId}`);
      if (response.data.success) {
        toast.success('Data deleted successfully!');
        fetchData();
      }
    } catch (error) {
      toast.error('Error deleting data: ' + error.message);
    }
  };

  const handleBulkDelete = async (orderIds) => {
    try {
      const response = await axios.post('/api/data/bulk-delete', { order_ids: orderIds });
      if (response.data.success) {
        toast.success(`${response.data.deleted_count} record(s) deleted successfully!`);
        fetchData();
      }
    } catch (error) {
      toast.error('Error deleting data: ' + error.message);
    }
  };

  const handleRunETL = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/etl/run');
      if (response.data.success) {
        toast.success(`ETL Pipeline completed! Processed ${response.data.records_processed} records`);
        fetchData();
      }
    } catch (error) {
      toast.error('Error running ETL: ' + error.message);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1>📊 ETL Pipeline Dashboard</h1>
            <p>Sales Data Management System</p>
          </div>
          <div className="header-actions">
            <button 
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
            <button 
              className="etl-button"
              onClick={handleRunETL}
              disabled={loading}
            >
              {loading ? '⏳ Running...' : '🚀 Run ETL Pipeline'}
            </button>
          </div>
        </div>
      </header>

      <nav className="tab-navigation">
        <button 
          className={activeTab === 'dashboard' ? 'active' : ''} 
          onClick={() => setActiveTab('dashboard')}
        >
          📈 Dashboard
        </button>
        <button 
          className={activeTab === 'data' ? 'active' : ''} 
          onClick={() => setActiveTab('data')}
        >
          📋 Data Table
        </button>
        <button 
          className={activeTab === 'add' ? 'active' : ''} 
          onClick={() => setActiveTab('add')}
        >
          ➕ Add Data
        </button>
        <button 
          className={activeTab === 'analytics' ? 'active' : ''} 
          onClick={() => setActiveTab('analytics')}
        >
          📊 Analytics
        </button>
      </nav>

      <main className="main-content">
        {loading && <div className="loading-overlay">Loading...</div>}
        
        {activeTab === 'dashboard' && (
          <Dashboard stats={stats} salesData={salesData} />
        )}
        
        {activeTab === 'data' && (
          <DataTable 
            data={salesData} 
            onDelete={handleDeleteData}
            onUpdate={handleUpdateData}
            onBulkDelete={handleBulkDelete}
            fetchData={fetchData}
          />
        )}
        
        {activeTab === 'add' && (
          <AddDataForm onAdd={handleAddData} fetchData={fetchData} />
        )}
        
        {activeTab === 'analytics' && (
          <Analytics salesData={salesData} />
        )}
      </main>

      <footer className="app-footer">
        <p>© 2025 ETL Pipeline Dashboard | Built with React & Flask</p>
      </footer>
    </div>
  );
}

export default App;

