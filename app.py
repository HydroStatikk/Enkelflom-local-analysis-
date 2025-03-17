import os
import io
import logging
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from utils.calculations import calculate_hydrological_analysis

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
                logger.info("Using example data option selected")
                
                # Try multiple possible paths for the Data.xlsx file
                possible_paths = [
                    os.path.join('attached_assets', 'Data.xlsx'),
                    os.path.join('.', 'attached_assets', 'Data.xlsx'),
                    os.path.join(os.path.dirname(__file__), 'attached_assets', 'Data.xlsx'),
                    'Data.xlsx'  # Last resort
                ]

                df = None
                for path in possible_paths:
                    try:
                        logger.info(f"Trying to load example data from: {path}")
                        if os.path.exists(path):
                            df = pd.read_excel(path)
                            logger.info(f"Successfully loaded data from: {path}")
                            break
                    except Exception as e:
                        logger.error(f"Failed to load from {path}: {str(e)}")

                if df is None:
                    flash('Error loading example data file', 'danger')
                    return redirect(url_for('index'))
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
                try:
                    df = pd.read_excel(file)
                    logger.info(f"Successfully loaded uploaded file: {file.filename}")
                except Exception as e:
                    logger.error(f"Error reading uploaded file: {str(e)}")
                    flash(f'Error reading uploaded file: {str(e)}', 'danger')
                    return redirect(url_for('index'))
            else:
                flash('Invalid file type. Please upload an Excel file (.xlsx, .xls)', 'danger')
                return redirect(url_for('index'))
        
        # Validate dataframe
        if df.empty:
            logger.error("The Excel file contains no data")
            flash('Error: The Excel file contains no data', 'danger')
            return redirect(url_for('index'))
            
        # Check required columns
        required_columns = ['latitude', 'longitude', 'specificDischarge']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            flash(f'Error: Missing required columns in data file: {", ".join(missing_columns)}', 'danger')
            return redirect(url_for('index'))
        
        # Get user inputs
        try:
            user_lat = float(request.form['latitude'])
            user_lon = float(request.form['longitude'])
            radius_km = float(request.form['radius'])
            catchment_area_km2 = float(request.form['catchmentArea'])
            climate_factor = float(request.form['climateFactor'])
            safety_factor = float(request.form['safetyFactor'])
            locality_scaling_factor = float(request.form['localityScalingFactor'])
            distance_scaling_factor = float(request.form['distanceScalingFactor'])
            
            logger.info(f"User inputs - lat: {user_lat}, lon: {user_lon}, radius: {radius_km}, catchment: {catchment_area_km2}")
        except ValueError as e:
            logger.error(f"Error in input parameters: {str(e)}")
            flash(f'Error in input parameters: {str(e)}', 'danger')
            return redirect(url_for('index'))
        
        # Perform hydrological analysis
        logger.info("Starting hydrological analysis")
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
        logger.info("Analysis completed successfully")
        
        # Don't store large data in session
        # Just store a flag that analysis was completed
        session['analysis_completed'] = True
        
        # Pass the full results directly to the template
        return render_template('results.html', results=results)
        
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}", exc_info=True)
        flash(f'Error in analysis: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/example-data')
def get_example_data():
    # Return some basic information from the actual data file
    try:
        logger.info("Loading example data for preview")
        
        # Try multiple possible paths for the Data.xlsx file
        possible_paths = [
            os.path.join('attached_assets', 'Data.xlsx'),
            os.path.join('.', 'attached_assets', 'Data.xlsx'),
            os.path.join(os.path.dirname(__file__), 'attached_assets', 'Data.xlsx'),
            'Data.xlsx'  # Last resort
        ]

        df = None
        for path in possible_paths:
            try:
                logger.info(f"Trying to load example data from: {path}")
                if os.path.exists(path):
                    df = pd.read_excel(path)
                    logger.info(f"Successfully loaded data from: {path}")
                    break
            except Exception as e:
                logger.error(f"Failed to load from {path}: {str(e)}")

        if df is None:
            logger.error("Could not load example data from any path")
            return jsonify({
                'status': 'error',
                'message': 'Could not find or load example data file'
            }), 500
        
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
        logger.error(f"Error loading example data: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
