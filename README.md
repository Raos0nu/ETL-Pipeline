# 📊 ETL Pipeline Dashboard

A modern, full-stack Data Engineering ETL Pipeline with a beautiful React frontend and Flask backend API. This application allows you to extract, transform, and load sales data while providing real-time analytics and visualizations.

## 🚀 **NEW: Modernized Architecture Available!**

This project has been modernized with enterprise-grade features including:
- ✅ **Configuration Management** - Environment-based configuration
- ✅ **Structured Logging** - JSON and text logging with context
- ✅ **SQLAlchemy ORM** - Modern database abstraction layer
- ✅ **Data Validation** - Pydantic models for request/response validation
- ✅ **Data Quality Checks** - Automatic data quality validation and reporting
- ✅ **Docker Support** - Containerization with Docker and Docker Compose
- ✅ **Multiple Data Sources** - Support for CSV, JSON, Excel, APIs, and databases

**👉 See [MODERNIZATION_GUIDE.md](MODERNIZATION_GUIDE.md) for details and migration instructions.**

## ✨ Features

### Core Features
- **📈 Interactive Dashboard** - View key metrics and recent orders at a glance
- **📋 Data Management** - Browse, search, sort, and manage sales records
- **➕ Add New Records** - User-friendly form with validation
- **✏️ Edit Records** - Inline editing directly in the data table
- **📊 Analytics & Visualization** - Beautiful charts showing sales insights
- **🚀 ETL Pipeline** - One-click ETL processing
- **💾 Dual Storage** - Data stored in both CSV and SQLite database

### Advanced Features
- **🌙 Dark Mode** - Toggle between light and dark themes
- **📄 Pagination** - Navigate through large datasets efficiently
- **☑️ Bulk Operations** - Select and delete multiple records at once
- **📥 CSV Import** - Upload CSV files to import multiple records
- **📈 Time Series Charts** - Track revenue and orders over time
- **🔔 Toast Notifications** - Modern, non-intrusive notifications
- **🔍 Advanced Search** - Search by product name or order ID
- **📊 Multiple Chart Types** - Bar, Line, Pie, and Area charts

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **Flask** - Web framework
- **Pandas** - Data manipulation
- **SQLite** - Database storage

### Frontend
- **React 18** - UI framework
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **React Hot Toast** - Toast notifications
- **CSS3** - Modern styling with gradients and animations

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.11 or higher
- Node.js 16 or higher
- npm or yarn

## 🚀 Installation & Setup

### Quick Start (Modernized App)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment (optional - defaults work for local dev)
cp .env.example .env

# 3. Run modernized app
python app_modern.py
```

**👉 See [QUICK_START_MODERN.md](QUICK_START_MODERN.md) for detailed quick start guide.**

### Docker (Recommended for Production)

```bash
docker-compose up --build
```

### Traditional Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd Data-Engineering-ETL-Pipeline-main
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build the React app
npm run build

# Go back to root directory
cd ..
```

## ▶️ Running the Application

### Start the Backend Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

Your dashboard will be accessible at: **http://localhost:5000**

### Development Mode (Optional)

If you want to run the frontend in development mode with hot-reload:

```bash
# In a separate terminal
cd frontend
npm start
```

This will start the React development server on `http://localhost:3000`

## 📖 Usage Guide

### Dashboard View
- See total orders, revenue, average order value, and items sold
- View the 5 most recent orders
- Get an overview of your sales data
- Toggle dark mode using the theme button in the header

### Data Table
- **Browse all sales records** with pagination (10, 25, 50, or 100 per page)
- **Search** by product name or order ID
- **Sort** by any column (click column headers)
- **Select multiple records** using checkboxes
- **Bulk delete** selected records
- **Edit records** inline by clicking the edit button
- **Delete individual records** with confirmation

### Add Data
- Fill in the form to add new sales records
- Real-time validation
- Automatic total price calculation
- Instant feedback on submission
- **CSV Import**: Upload a CSV file to import multiple records at once
  - CSV should have columns: `order_id`, `product`, `quantity`, `price`

### Analytics
- **Revenue Over Time** - Area chart showing revenue trends
- **Orders Over Time** - Line chart tracking order counts
- **Revenue by Product** - Bar chart comparing product revenue
- **Sales Distribution** - Pie chart showing revenue distribution
- **Quantity Sold** - Bar chart of units sold per product
- **Orders per Product** - Line chart of order frequency
- **Product Performance Table** - Detailed summary with sortable columns

### ETL Pipeline
Click the "🚀 Run ETL Pipeline" button to:
1. Extract data from CSV
2. Transform data (calculate total_price)
3. Load data into SQLite database

## 📁 Project Structure

```
Data-Engineering-ETL-Pipeline-main/
├── app.py                  # Flask backend server
├── extract.py              # Data extraction module
├── transform.py            # Data transformation module
├── load_data.py           # CLI tool (legacy)
├── requirements.txt        # Python dependencies
├── sales.db               # SQLite database
├── data/
│   └── sample_sales.csv   # Sales data CSV
├── api/
│   └── index.py          # Vercel serverless function
└── frontend/
    ├── package.json       # Node dependencies
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js         # Main React component
        ├── App.css        # Main styles
        ├── index.js       # React entry point
        ├── index.css      # Global styles
        └── components/
            ├── Dashboard.js       # Dashboard component
            ├── Dashboard.css
            ├── DataTable.js       # Data table component
            ├── DataTable.css
            ├── AddDataForm.js     # Add data form
            ├── AddDataForm.css
            ├── Analytics.js       # Analytics & charts
            └── Analytics.css
```

## 🔌 API Endpoints

### GET `/api/health`
Health check endpoint

### GET `/api/data`
Get all sales data with optional pagination and filtering
- Query parameters:
  - `page` (default: 1) - Page number
  - `per_page` (default: 50) - Records per page
  - `start_date` (optional) - Filter start date
  - `end_date` (optional) - Filter end date

### GET `/api/data/raw`
Get raw sales data without transformation

### POST `/api/data`
Add new sales record
```json
{
  "order_id": 101,
  "product": "Laptop",
  "quantity": 2,
  "price": 999.99
}
```

### PUT `/api/data/<order_id>`
Update a sales record
```json
{
  "product": "Laptop Pro",
  "quantity": 3,
  "price": 1299.99
}
```

### DELETE `/api/data/<order_id>`
Delete a sales record

### POST `/api/data/bulk-delete`
Delete multiple sales records
```json
{
  "order_ids": [101, 102, 103]
}
```

### POST `/api/data/import`
Import data from CSV file
- Content-Type: `multipart/form-data`
- File field: `file`

### POST `/api/etl/run`
Run the complete ETL pipeline

### GET `/api/analytics/products`
Get product-wise analytics

### GET `/api/analytics/timeseries`
Get time series analytics (revenue and orders over time)

## 🎨 UI Features

### Dark Mode
- Toggle between light and dark themes
- Preference saved in localStorage
- Smooth transitions between themes
- All components support dark mode

### Responsive Design
- **Desktop**: Full layout with all features
- **Tablet**: Optimized 2-column layouts
- **Mobile**: Single column, touch-friendly interface

### Notifications
- Toast notifications for all actions
- Success, error, and info messages
- Auto-dismiss after a few seconds
- Non-intrusive design

### Data Table Features
- **Pagination**: Navigate through pages
- **Sorting**: Click column headers to sort
- **Search**: Real-time filtering
- **Selection**: Checkbox selection for bulk operations
- **Inline Editing**: Edit records directly in the table
- **Bulk Delete**: Delete multiple records at once

### Charts & Visualizations
- **Interactive Charts**: Hover for details
- **Responsive**: Adapts to screen size
- **Multiple Types**: Bar, Line, Pie, Area charts
- **Time Series**: Track trends over time
- **Export Ready**: Professional quality visualizations

## 🎯 Key Features Explained

### Edit Records
1. Click the ✏️ edit button on any row
2. Modify the fields inline
3. Click ✓ to save or ✕ to cancel
4. Changes are saved immediately

### Bulk Operations
1. Select records using checkboxes
2. Use "Select All" to select all visible records
3. Click "Delete Selected" to remove multiple records
4. Confirmation dialog prevents accidental deletions

### CSV Import
1. Go to "Add Data" tab
2. Click "Choose CSV File" in the import section
3. Select a CSV file with columns: order_id, product, quantity, price
4. Records are imported automatically
5. Duplicate order_ids are handled (last one wins)

### Pagination
- Choose records per page: 10, 25, 50, or 100
- Navigate using Previous/Next buttons
- Jump to specific pages using page numbers
- Page info shows current page and total pages

## 🔧 Development

### Running in Development Mode

**Backend:**
```bash
python app.py
```

**Frontend:**
```bash
cd frontend
npm start
```

### Building for Production

```bash
cd frontend
npm run build
```

The built files will be in `frontend/build/` and served by Flask.

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**
   - Change the port in `app.py`: `app.run(debug=True, port=5001)`

2. **Module not found errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - For frontend: `cd frontend && npm install`

3. **Database errors**
   - Delete `sales.db` and restart the server (it will be recreated)

4. **CSV import fails**
   - Ensure CSV has correct columns: order_id, product, quantity, price
   - Check file encoding (should be UTF-8)

## 📝 Data Format

### CSV Format
```csv
order_id,product,quantity,price
1,Laptop,2,999.99
2,Mouse,5,29.99
3,Keyboard,3,79.99
```

### JSON Format (API)
```json
{
  "order_id": 1,
  "product": "Laptop",
  "quantity": 2,
  "price": 999.99
}
```

## 🚀 Deployment

### Vercel Deployment
The project includes Vercel configuration. See `vercel.json` and `api/index.py` for serverless function setup.

### Other Platforms
- **Heroku**: Use Procfile and requirements.txt
- **Docker**: Create Dockerfile for containerized deployment
- **AWS/GCP**: Use standard Flask deployment practices

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Enjoy managing your sales data with style! 🎉**
