import os
import io
import logging
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from utils.calculations import calculate_hydrological_analysis

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Check if file is uploaded
        if 'file' not in request.files:
            # If no file, check if using example data
            if request.form.get('useExampleData') == 'true':
                # Use actual Data.xlsx file
                file_path = os.path.join('attached_assets', 'Data.xlsx')
                df = pd.read_excel(file_path)
            else:
                flash('No file uploaded and example data not selected', 'danger')
                return redirect(url_for('index'))
        else:
            file = request.files['file']
            
            # If user doesn't select a file
            if file.filename == '':
                flash('No file selected', 'danger')
                return redirect(url_for('index'))
                
            if file and allowed_file(file.filename):
                # Read the Excel file
                df = pd.read_excel(file)
            else:
                flash('Invalid file type. Please upload an Excel file (.xlsx, .xls)', 'danger')
                return redirect(url_for('index'))
        
        # Get user inputs
        user_lat = float(request.form['latitude'])
        user_lon = float(request.form['longitude'])
        radius_km = float(request.form['radius'])
        catchment_area_km2 = float(request.form['catchmentArea'])
        climate_factor = float(request.form['climateFactor'])
        safety_factor = float(request.form['safetyFactor'])
        locality_scaling_factor = float(request.form['localityScalingFactor'])
        distance_scaling_factor = float(request.form['distanceScalingFactor'])
        
        # Perform hydrological analysis
        results = calculate_hydrological_analysis(
            df, 
            user_lat, 
            user_lon, 
            radius_km, 
            catchment_area_km2,
            climate_factor,
            safety_factor,
            locality_scaling_factor,
            distance_scaling_factor
        )
        
        # Store results in session
        session['results'] = results
        
        return render_template('results.html', results=results)
        
    except Exception as e:
        logging.error(f"Error in analysis: {str(e)}")
        flash(f'Error in analysis: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/example-data')
def get_example_data():
    # Return some basic information from the actual data file
    try:
        # Use the actual Data.xlsx file
        file_path = os.path.join('attached_assets', 'Data.xlsx')
        df = pd.read_excel(file_path)
        
        # Get a sample of the data for preview
        sample_data = df.head(5).to_dict(orient='records')
        columns = df.columns.tolist()
        
        return jsonify({
            'status': 'success',
            'columns': columns,
            'sample_data': sample_data,
            'total_rows': len(df)
        })
    except Exception as e:
        logging.error(f"Error loading example data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
