from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import json
import time

app = Flask(__name__)

def load_astro_data():
    """Load astro data from the text file"""
    try:
        df = pd.read_csv('kp_astro.txt', sep='\t')
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def search_deepseek(query):
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer YOUR_DEEPSEEK_API_KEY'
        }
        
        payload = {
            'query': query,
            'context': 'astrological_data'
        }
        
        response = requests.post(
            'https://chat.deepseek.com/api/chat', 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Error connecting to DeepSeek: {str(e)}"}


@app.route('/')
def index():
    """Main page route"""
    df = load_astro_data()
    
    # Get unique planets for the select dropdown
    planets = []
    if not df.empty:
        planets = sorted(df['Planet'].unique().tolist())
    
    return render_template('index.html', 
                         data=df.to_dict('records') if not df.empty else [], 
                         planets=planets)

@app.route('/filter_data', methods=['POST'])
def filter_data():
    """Filter data based on selected planet"""
    try:
        selected_planet = request.json.get('planet', '')
        df = load_astro_data()
        
        if selected_planet and selected_planet != 'all':
            filtered_df = df[df['Planet'] == selected_planet]
        else:
            filtered_df = df
            
        return jsonify({
            'success': True,
            'data': filtered_df.to_dict('records')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/search_deepseek', methods=['POST'])
def search_deepseek_route():
    """Search using DeepSeek AI"""
    try:
        query = request.json.get('query', '')
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            })
        
        # Get current astro data for context
        df = load_astro_data()
        context = f"Astrological Data Context:\n{df.to_string()}\n\nUser Query: {query}"
        
        # Search DeepSeek
        result = search_deepseek(context)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
