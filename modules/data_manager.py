import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
import uuid
import os

class DataManager:
    def __init__(self, db_path='moderation_data.db'):
        """Initialize the data manager with SQLite database."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                content TEXT,
                filename TEXT,
                is_inappropriate BOOLEAN NOT NULL,
                confidence_score REAL NOT NULL,
                reasons TEXT,
                status TEXT DEFAULT 'pending',
                timestamp TEXT NOT NULL,
                details TEXT
            )
        ''')
        
        # Create user actions table for audit trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id TEXT PRIMARY KEY,
                analysis_id TEXT,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analysis_results (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_analysis_result(self, content_type, content, is_inappropriate, 
                            confidence_score, reasons, filename=None, status='pending'):
        """Store analysis result in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        reasons_json = json.dumps(reasons) if reasons else json.dumps([])
        
        cursor.execute('''
            INSERT INTO analysis_results 
            (id, content_type, content, filename, is_inappropriate, confidence_score, 
             reasons, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (analysis_id, content_type, content, filename, is_inappropriate, 
              confidence_score, reasons_json, status, timestamp))
        
        conn.commit()
        conn.close()
        
        return analysis_id
    
    def get_analysis_result(self, analysis_id):
        """Get a specific analysis result by ID."""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT * FROM analysis_results WHERE id = ?
        ''', conn, params=(analysis_id,))
        
        conn.close()
        
        if not df.empty:
            # Parse JSON reasons
            df['reasons'] = df['reasons'].apply(lambda x: json.loads(x) if x else [])
            return df.iloc[0]
        
        return None
    
    def get_all_analysis(self):
        """Get all analysis results."""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT * FROM analysis_results 
            ORDER BY timestamp DESC
        ''', conn)
        
        conn.close()
        
        if not df.empty:
            # Parse JSON reasons
            df['reasons'] = df['reasons'].apply(lambda x: json.loads(x) if x else [])
        
        return df
    
    def get_recent_analysis(self, hours=24):
        """Get analysis results from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT * FROM analysis_results 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', conn, params=(cutoff_str,))
        
        conn.close()
        
        if not df.empty:
            # Parse JSON reasons
            df['reasons'] = df['reasons'].apply(lambda x: json.loads(x) if x else [])
        
        return df
    
    def update_status(self, analysis_id, new_status, notes=None):
        """Update the status of an analysis result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update the analysis result
        cursor.execute('''
            UPDATE analysis_results 
            SET status = ? 
            WHERE id = ?
        ''', (new_status, analysis_id))
        
        # Log the user action
        action_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO user_actions 
            (id, analysis_id, action, timestamp, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (action_id, analysis_id, f'status_change_to_{new_status}', timestamp, notes))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self, days=30):
        """Get statistics for the dashboard."""
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_time.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        
        # Get basic stats
        stats_query = '''
            SELECT 
                COUNT(*) as total_analyzed,
                SUM(CASE WHEN is_inappropriate = 1 THEN 1 ELSE 0 END) as inappropriate_count,
                AVG(confidence_score) as avg_confidence,
                content_type,
                COUNT(*) as type_count
            FROM analysis_results 
            WHERE timestamp >= ?
            GROUP BY content_type
        '''
        
        df = pd.read_sql_query(stats_query, conn, params=(cutoff_str,))
        conn.close()
        
        return df
    
    def export_data(self, output_path, start_date=None, end_date=None):
        """Export analysis data to CSV."""
        conn = sqlite3.connect(self.db_path)
        
        query = 'SELECT * FROM analysis_results'
        params = []
        
        if start_date or end_date:
            query += ' WHERE '
            conditions = []
            
            if start_date:
                conditions.append('timestamp >= ?')
                params.append(start_date.isoformat())
            
            if end_date:
                conditions.append('timestamp <= ?')
                params.append(end_date.isoformat())
            
            query += ' AND '.join(conditions)
        
        query += ' ORDER BY timestamp DESC'
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            # Parse JSON reasons for export
            df['reasons'] = df['reasons'].apply(lambda x: ', '.join(json.loads(x)) if x else '')
            df.to_csv(output_path, index=False)
        
        return len(df)
    
    def cleanup_old_data(self, days_to_keep=90):
        """Clean up old data to prevent database bloat."""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_time.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete old analysis results
        cursor.execute('''
            DELETE FROM analysis_results 
            WHERE timestamp < ?
        ''', (cutoff_str,))
        
        # Delete old user actions
        cursor.execute('''
            DELETE FROM user_actions 
            WHERE timestamp < ?
        ''', (cutoff_str,))
        
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def get_flagged_content_summary(self, days=7):
        """Get a summary of recently flagged content."""
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_time.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                content_type,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence,
                reasons
            FROM analysis_results 
            WHERE timestamp >= ? AND is_inappropriate = 1
            GROUP BY content_type, reasons
            ORDER BY count DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(cutoff_str,))
        conn.close()
        
        if not df.empty:
            df['reasons'] = df['reasons'].apply(lambda x: json.loads(x) if x else [])
        
        return df
