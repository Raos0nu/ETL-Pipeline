from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import extract
import transform
import sqlite3
import os
from datetime import datetime
import io
import csv

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

DATA_FILE = 'data/sample_sales.csv'
DB_FILE = 'sales.db'

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product TEXT,
            quantity INTEGER,
            price REAL,
            total_price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def serve():
    """Serve React frontend"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all sales data with optional pagination and filtering"""
    try:
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        
        # Date filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date or end_date:
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                if start_date:
                    df = df[df['created_at'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['created_at'] <= pd.to_datetime(end_date)]
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        total_records = len(df)
        total_pages = (total_records + per_page - 1) // per_page
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_df = df.iloc[start_idx:end_idx]
        data = paginated_df.to_dict('records')
        
        # Calculate statistics
        stats = {
            'total_orders': total_records,
            'total_revenue': float(df['total_price'].sum()),
            'average_order_value': float(df['total_price'].mean()),
            'total_items_sold': int(df['quantity'].sum())
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'stats': stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_records': total_records,
                'total_pages': total_pages
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/raw', methods=['GET'])
def get_raw_data():
    """Get raw sales data without transformation"""
    try:
        df = extract.extract(DATA_FILE)
        data = df.to_dict('records')
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data', methods=['POST'])
def add_data():
    """Add new sales record"""
    try:
        data = request.json
        
        # Validate input
        required_fields = ['order_id', 'product', 'quantity', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Load existing data
        df = extract.extract(DATA_FILE)
        
        # Create new row
        new_row = {
            'order_id': int(data['order_id']),
            'product': data['product'],
            'quantity': int(data['quantity']),
            'price': float(data['price'])
        }
        
        new_row_df = pd.DataFrame([new_row])
        df = pd.concat([df, new_row_df], ignore_index=True)
        
        # Save to CSV
        df.to_csv(DATA_FILE, index=False)
        
        # Also save to database
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({'success': True, 'message': 'Data added successfully', 'data': new_row})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/<int:order_id>', methods=['PUT'])
def update_data(order_id):
    """Update a sales record"""
    try:
        data = request.json
        df = extract.extract(DATA_FILE)
        
        if order_id not in df['order_id'].values:
            return jsonify({'success': False, 'error': 'Order ID not found'}), 404
        
        # Update the record
        idx = df[df['order_id'] == order_id].index[0]
        if 'product' in data:
            df.at[idx, 'product'] = data['product']
        if 'quantity' in data:
            df.at[idx, 'quantity'] = int(data['quantity'])
        if 'price' in data:
            df.at[idx, 'price'] = float(data['price'])
        
        # Save to CSV
        df.to_csv(DATA_FILE, index=False)
        
        # Transform and save to DB
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({'success': True, 'message': f'Order {order_id} updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/<int:order_id>', methods=['DELETE'])
def delete_data(order_id):
    """Delete a sales record"""
    try:
        df = extract.extract(DATA_FILE)
        
        if order_id not in df['order_id'].values:
            return jsonify({'success': False, 'error': 'Order ID not found'}), 404
        
        df = df[df['order_id'] != order_id]
        df.to_csv(DATA_FILE, index=False)
        
        # Update database
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({'success': True, 'message': f'Order {order_id} deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/bulk-delete', methods=['POST'])
def bulk_delete_data():
    """Delete multiple sales records"""
    try:
        data = request.json
        order_ids = data.get('order_ids', [])
        
        if not order_ids:
            return jsonify({'success': False, 'error': 'No order IDs provided'}), 400
        
        df = extract.extract(DATA_FILE)
        initial_count = len(df)
        df = df[~df['order_id'].isin(order_ids)]
        deleted_count = initial_count - len(df)
        
        df.to_csv(DATA_FILE, index=False)
        
        # Update database
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} order(s) deleted successfully',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etl/run', methods=['POST'])
def run_etl():
    """Run the complete ETL pipeline"""
    try:
        # Extract
        df = extract.extract(DATA_FILE)
        
        # Transform
        df = transform.transform(df)
        
        # Load to database
        save_to_db(df)
        
        return jsonify({
            'success': True,
            'message': 'ETL pipeline completed successfully',
            'records_processed': len(df)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/products', methods=['GET'])
def get_product_analytics():
    """Get product-wise analytics"""
    try:
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        
        # Group by product
        product_stats = df.groupby('product').agg({
            'quantity': 'sum',
            'total_price': 'sum',
            'order_id': 'count'
        }).reset_index()
        
        product_stats.columns = ['product', 'total_quantity', 'total_revenue', 'order_count']
        
        return jsonify({
            'success': True,
            'data': product_stats.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/timeseries', methods=['GET'])
def get_timeseries_analytics():
    """Get time series analytics"""
    try:
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        
        # Add date column if not exists (use created_at or generate from order_id)
        if 'created_at' not in df.columns:
            df['created_at'] = pd.to_datetime('2024-01-01') + pd.to_timedelta(df['order_id'], unit='D')
        else:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Group by date
        df['date'] = df['created_at'].dt.date
        daily_stats = df.groupby('date').agg({
            'total_price': 'sum',
            'order_id': 'count',
            'quantity': 'sum'
        }).reset_index()
        
        daily_stats.columns = ['date', 'revenue', 'orders', 'quantity']
        daily_stats['date'] = daily_stats['date'].astype(str)
        
        return jsonify({
            'success': True,
            'data': daily_stats.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/import', methods=['POST'])
def import_csv():
    """Import data from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Read CSV
        file_content = file.read()
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        stream = io.StringIO(file_content, newline=None)
        csv_input = csv.DictReader(stream)
        
        # Load existing data
        df = extract.extract(DATA_FILE)
        
        # Prepare new rows
        new_rows = []
        for row in csv_input:
            try:
                new_row = {
                    'order_id': int(row.get('order_id', 0)),
                    'product': row.get('product', ''),
                    'quantity': int(row.get('quantity', 0)),
                    'price': float(row.get('price', 0))
                }
                new_rows.append(new_row)
            except (ValueError, KeyError) as e:
                continue
        
        if not new_rows:
            return jsonify({'success': False, 'error': 'No valid rows found in CSV'}), 400
        
        # Add new rows
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        
        # Remove duplicates based on order_id (keep last)
        df = df.drop_duplicates(subset=['order_id'], keep='last')
        
        # Save to CSV
        df.to_csv(DATA_FILE, index=False)
        
        # Transform and save to DB
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({
            'success': True,
            'message': f'{len(new_rows)} record(s) imported successfully',
            'imported_count': len(new_rows)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def save_to_db(df):
    """Save DataFrame to SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    
    # Clear existing data
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sales')
    
    # Insert new data
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO sales (order_id, product, quantity, price, total_price)
            VALUES (?, ?, ?, ?, ?)
        ''', (row['order_id'], row['product'], row['quantity'], row['price'], row['total_price']))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Starting ETL Pipeline Server...")
    print("Dashboard available at: http://localhost:5000")
    print("Open your browser to view the dashboard!")
    app.run(debug=True, port=5000)

