"""
Vercel serverless function for Flask API
This file handles all API routes for the ETL Pipeline Dashboard
"""
import sys
import os

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

# Create Flask app
app = Flask(__name__)
CORS(app)

# Use absolute paths for Vercel
DATA_FILE = os.path.join(parent_dir, 'data', 'sample_sales.csv')
DB_FILE = os.path.join(parent_dir, 'sales.db')

def init_db():
    """Initialize SQLite database"""
    try:
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

# Initialize database
init_db()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all sales data"""
    try:
        df = extract.extract(DATA_FILE)
        df = transform.transform(df)
        data = df.to_dict('records')
        
        # Calculate statistics
        stats = {
            'total_orders': len(df),
            'total_revenue': float(df['total_price'].sum()),
            'average_order_value': float(df['total_price'].mean()),
            'total_items_sold': int(df['quantity'].sum())
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'stats': stats
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

@app.route('/api/data/<int:order_id>', methods=['DELETE'])
def delete_data(order_id):
    """Delete a sales record"""
    try:
        df = extract.extract(DATA_FILE)
        
        if order_id not in df['order_id'].values:
            return jsonify({'success': False, 'error': 'Order ID not found'}), 404
        
        df = df[df['order_id'] != order_id]
        df.to_csv(DATA_FILE, index=False)
        
        return jsonify({'success': True, 'message': f'Order {order_id} deleted successfully'})
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

def save_to_db(df):
    """Save DataFrame to SQLite database"""
    try:
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
    except Exception as e:
        print(f"Database save error: {e}")

# Export app for Vercel - this is the key for Vercel Python runtime
# Vercel will automatically detect and use this
app = app
