from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
DEEPSEEK_API_URL = "https://chat.deepseek.com/v1/chat/completions"  # Example endpoint
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'your_api_key_here')
DATA_FILE = 'kp_astro.txt'

def load_astro_data():
    """Load and preprocess astro data"""
    try:
        df = pd.read_csv(DATA_FILE, sep='\t')
        
        # Convert to consistent datetime format
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df['Date'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        df['Time'] = df['DateTime'].dt.strftime('%H:%M:%S')
        
        return df.sort_values('DateTime')
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def query_deepseek(prompt, astro_context=""):
    """Query DeepSeek API with error handling"""
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    messages = [
        {
            "role": "system",
            "content": f"""You are an expert astrological AI analyst. Analyze this KP astro data:
            {astro_context}
            Provide detailed interpretations focusing on planetary influences, timing, and practical implications.
            """
        },
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"API Error: {str(e)}"
    except (KeyError, IndexError) as e:
        return "Error parsing API response"

@app.route('/')
def index():
    """Main dashboard page"""
    df = load_astro_data()
    latest_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Prepare summary stats
    stats = {
        'planets': df['Planet'].nunique(),
        'entries': len(df),
        'date_range': f"{df['Date'].min()} to {df['Date'].max()}",
        'active_mode': "Hybrid AI System" if DEEPSEEK_API_KEY else "Local Analysis"
    }
    
    return render_template(
        'index.html',
        data=df.to_dict('records'),
        planets=sorted(df['Planet'].unique()),
        stats=stats,
        last_updated=latest_update
    )

@app.route('/api/filter', methods=['POST'])
def filter_data():
    """API endpoint for filtering data"""
    try:
        filters = request.get_json()
        df = load_astro_data()
        
        # Apply filters
        if filters.get('planet') and filters['planet'] != 'all':
            df = df[df['Planet'] == filters['planet']]
            
        if filters.get('date'):
            df = df[df['Date'] == filters['date']]
            
        if filters.get('motion'):
            df = df[df['Motion'] == filters['motion']]
            
        return jsonify({
            'success': True,
            'data': df.to_dict('records'),
            'count': len(df)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """API endpoint for DeepSeek analysis"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            raise ValueError("Query cannot be empty")
            
        # Get current astro context
        df = load_astro_data()
        context = df.to_string()
        
        # Get AI analysis
        start_time = time.time()
        analysis = query_deepseek(query, context)
        response_time = round(time.time() - start_time, 2)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'response_time': f"{response_time}s",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
