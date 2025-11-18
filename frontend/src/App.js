import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import DataTable from './components/DataTable';
import AddDataForm from './components/AddDataForm';
import Analytics from './components/Analytics';
import axios from 'axios';

function App() {
  const [salesData, setSalesData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [notification, setNotification] = useState(null);

  const showNotification = useCallback((message, type) => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/data');
      if (response.data.success) {
        setSalesData(response.data.data);
        setStats(response.data.stats);
      }
    } catch (error) {
      showNotification('Error fetching data: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [showNotification]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddData = async (newData) => {
    try {
      const response = await axios.post('/api/data', newData);
      if (response.data.success) {
        showNotification('Data added successfully!', 'success');
        fetchData();
        return true;
      }
    } catch (error) {
      showNotification('Error adding data: ' + error.message, 'error');
      return false;
    }
  };

  const handleDeleteData = async (orderId) => {
    try {
      const response = await axios.delete(`/api/data/${orderId}`);
      if (response.data.success) {
        showNotification('Data deleted successfully!', 'success');
        fetchData();
      }
    } catch (error) {
      showNotification('Error deleting data: ' + error.message, 'error');
    }
  };

  const handleRunETL = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/etl/run');
      if (response.data.success) {
        showNotification(`ETL Pipeline completed! Processed ${response.data.records_processed} records`, 'success');
        fetchData();
      }
    } catch (error) {
      showNotification('Error running ETL: ' + error.message, 'error');
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
          <button 
            className="etl-button"
            onClick={handleRunETL}
            disabled={loading}
          >
            {loading ? '⏳ Running...' : '🚀 Run ETL Pipeline'}
          </button>
        </div>
      </header>

      {notification && (
        <div className={`notification ${notification.type}`}>
          {notification.message}
        </div>
      )}

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
          <DataTable data={salesData} onDelete={handleDeleteData} />
        )}
        
        {activeTab === 'add' && (
          <AddDataForm onAdd={handleAddData} />
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

