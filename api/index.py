"""
Vercel serverless function for Flask API
This file handles all API routes for the ETL Pipeline Dashboard
"""
import sys
import os
import shutil

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import extract
import transform
import sqlite3
from datetime import datetime
import io
import csv

# Create Flask app
app = Flask(__name__)
CORS(app)

# Use /tmp directory for Vercel (writable filesystem)
# Copy original CSV to /tmp on first access if it doesn't exist
TMP_DIR = '/tmp'
DATA_FILE_ORIGINAL = os.path.join(parent_dir, 'data', 'sample_sales.csv')
DATA_FILE = os.path.join(TMP_DIR, 'sample_sales.csv')
DB_FILE = os.path.join(TMP_DIR, 'sales.db')

def ensure_data_file():
    """Ensure CSV file exists in /tmp, copy from original if needed"""
    if not os.path.exists(DATA_FILE):
        try:
            # Create /tmp directory if it doesn't exist
            os.makedirs(TMP_DIR, exist_ok=True)
            # Copy original file to /tmp
            if os.path.exists(DATA_FILE_ORIGINAL):
                shutil.copy2(DATA_FILE_ORIGINAL, DATA_FILE)
            else:
                # Create empty CSV if original doesn't exist
                pd.DataFrame(columns=['order_id', 'product', 'quantity', 'price']).to_csv(DATA_FILE, index=False)
        except Exception as e:
            print(f"Error ensuring data file: {e}")
            # Create empty CSV as fallback
            pd.DataFrame(columns=['order_id', 'product', 'quantity', 'price']).to_csv(DATA_FILE, index=False)

def init_db():
    """Initialize SQLite database"""
    try:
        ensure_data_file()  # Ensure data file exists first
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
    except Exception as e:
        print(f"Database init error: {e}")

# Initialize database on module load
init_db()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all sales data"""
    try:
        ensure_data_file()
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        data = df.to_dict('records')
        
        # Calculate statistics
        stats = {
            'total_orders': len(df),
            'total_revenue': float(df['total_price'].sum()) if len(df) > 0 else 0.0,
            'average_order_value': float(df['total_price'].mean()) if len(df) > 0 else 0.0,
            'total_items_sold': int(df['quantity'].sum()) if len(df) > 0 else 0
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'stats': stats
        })
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in get_data: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/raw', methods=['GET'])
def get_raw_data():
    """Get raw sales data without transformation"""
    try:
        ensure_data_file()
        df = extract.extract(DATA_FILE)
        data = df.to_dict('records')
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in get_raw_data: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data', methods=['POST'])
def add_data():
    """Add new sales record"""
    try:
        ensure_data_file()
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
        
        # Save to CSV in /tmp
        df.to_csv(DATA_FILE, index=False)
        
        # Also save to database
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({'success': True, 'message': 'Data added successfully', 'data': new_row})
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in add_data: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/<int:order_id>', methods=['PUT'])
def update_data(order_id):
    """Update a sales record"""
    try:
        ensure_data_file()
        data = request.json
        df = extract.extract(DATA_FILE)
        
        if len(df) == 0 or order_id not in df['order_id'].values:
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
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in update_data: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/<int:order_id>', methods=['DELETE'])
def delete_data(order_id):
    """Delete a sales record"""
    try:
        ensure_data_file()
        df = extract.extract(DATA_FILE)
        
        if len(df) == 0 or order_id not in df['order_id'].values:
            return jsonify({'success': False, 'error': 'Order ID not found'}), 404
        
        df = df[df['order_id'] != order_id]
        df.to_csv(DATA_FILE, index=False)
        
        # Update database
        df_transformed = transform.transform(df.copy())
        save_to_db(df_transformed)
        
        return jsonify({'success': True, 'message': f'Order {order_id} deleted successfully'})
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in delete_data: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/bulk-delete', methods=['POST'])
def bulk_delete_data():
    """Delete multiple sales records"""
    try:
        ensure_data_file()
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
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in bulk_delete_data: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etl/run', methods=['POST'])
def run_etl():
    """Run the complete ETL pipeline"""
    try:
        ensure_data_file()
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
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in run_etl: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/products', methods=['GET'])
def get_product_analytics():
    """Get product-wise analytics"""
    try:
        ensure_data_file()
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        
        if len(df) == 0:
            return jsonify({
                'success': True,
                'data': []
            })
        
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
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in get_product_analytics: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/timeseries', methods=['GET'])
def get_timeseries_analytics():
    """Get time series analytics"""
    try:
        ensure_data_file()
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        
        if len(df) == 0:
            return jsonify({
                'success': True,
                'data': []
            })
        
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
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in get_timeseries_analytics: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data/import', methods=['POST'])
def import_csv():
    """Import data from CSV file"""
    try:
        ensure_data_file()
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
        
        # Save to CSV in /tmp
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
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in import_csv: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500

def save_to_db(df):
    """Save DataFrame to SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Clear existing data
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sales')
        
        # Insert new data
        if len(df) > 0:
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO sales (order_id, product, quantity, price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['order_id'], row['product'], row['quantity'], row['price'], row['total_price']))
        
        conn.commit()
        conn.close()
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Database save error: {error_msg}")

# Vercel Python runtime handler
# Vercel's Python runtime supports WSGI applications
# We export the Flask app directly - Vercel will handle WSGI automatically
# The vercel.json rewrite rule routes /api/* to this file
# Flask routes are defined with /api prefix, so they should match correctly

# Note: Vercel's Python runtime automatically detects Flask apps
# Make sure the routes match the rewrite pattern in vercel.json
