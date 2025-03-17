import pandas as pd
import numpy as np
import json
import logging

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    R = 6371  # Radius of Earth in km
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c  # Distance in km

def calculate_hydrological_analysis(df, user_lat, user_lon, radius_km, catchment_area_km2, 
                                   climate_factor, safety_factor, locality_scaling_factor, 
                                   distance_scaling_factor):
    """
    Perform hydrological analysis based on the given parameters
    """
    # Ensure required columns exist (with fallbacks for missing columns)
    required_columns = ['latitude', 'longitude', 'specificDischarge']
    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Required column '{column}' not found in the input file")

    # Map station ID/name to match our expected naming convention
    # Use 'stationId' as 'stationNumber' if available
    if 'stationNumber' not in df.columns:
        if 'stationId' in df.columns:
            df['stationNumber'] = df['stationId'].astype(str)
        else:
            df['stationNumber'] = [f"{i+1}" for i in range(len(df))]
            
    # Make sure we have stationName
    if 'stationName' not in df.columns:
        df['stationName'] = [f"Station {i+1}" for i in range(len(df))]
            
    # Calculate distance to user for each station
    df["distance_to_user"] = df.apply(
        lambda row: haversine(user_lat, user_lon, row["latitude"], row["longitude"]), 
        axis=1
    )
    
    # Filter stations within the radius
    df_filtered = df[df["distance_to_user"] <= radius_km].copy()
    
    # If no stations are found within the radius, return error
    if len(df_filtered) == 0:
        raise ValueError(f"No stations found within {radius_km} km radius")
    
    # Calculate locality weights
    df_filtered["locality_weight"] = np.exp(-df_filtered["distance_to_user"] / distance_scaling_factor)
    df_filtered["locality_weight_scaled"] = df_filtered["locality_weight"] * locality_scaling_factor
    df_filtered["locality_weight_normalized"] = df_filtered["locality_weight_scaled"] / df_filtered["locality_weight_scaled"].sum()
    
    # Calculate weighted average specific discharge
    weighted_avg_specific_discharge = np.average(
        df_filtered["specificDischarge"], 
        weights=df_filtered["locality_weight_normalized"]
    )
    
    # Calculate average and standard deviation of specific discharge
    average_discharge = df_filtered["specificDischarge"].mean()
    std_discharge = df_filtered["specificDischarge"].std()
    
    # Calculate average discharge over the catchment area
    average_discharge_catchment = average_discharge * catchment_area_km2 / 1000  # Convert to cubic meters per second
    
    # Columns to calculate
    columns_to_calculate = [
        "Qm/Qn", "Q5/Qn", "Q10/Qn", "Q20/Qn", "Q50/Qn", "Q100/Qn", "Q200/Qn"
    ]
    
    # Prepare results dictionary
    results = {
        'filtered_stations': df_filtered.to_dict(orient='records'),
        'user_inputs': {
            'latitude': user_lat,
            'longitude': user_lon,
            'radius_km': radius_km,
            'catchment_area_km2': catchment_area_km2,
            'climate_factor': climate_factor,
            'safety_factor': safety_factor,
            'locality_scaling_factor': locality_scaling_factor,
            'distance_scaling_factor': distance_scaling_factor
        },
        'discharge_summary': {
            'weighted_avg_specific_discharge': weighted_avg_specific_discharge,
            'average_discharge': average_discharge,
            'std_discharge': std_discharge,
            'average_discharge_catchment': average_discharge_catchment
        },
        'flood_metrics': {}
    }
    
    # Calculate metrics for each column
    for column in columns_to_calculate:
        # Check if the column exists in the dataframe
        if column not in df_filtered.columns:
            logging.warning(f"Column '{column}' not found in the input file. Skipping calculations for this metric.")
            continue
            
        average_value = df_filtered[column].mean()
        std_dev = df_filtered[column].std()
        
        # Calculate the required expression for each column
        result = (average_value + std_dev) / average_value
        
        # Calculate flood discharge
        flood_discharge = average_discharge_catchment * average_value
        
        # Calculate deviated flood discharge
        deviated_flood_discharge = flood_discharge * result
        
        # Calculate dimensioned flood discharge
        dimensioned_flood_discharge = flood_discharge * climate_factor * safety_factor
        
        # Calculate dimensioned deviated flood discharge
        dimensioned_deviated_flood_discharge = deviated_flood_discharge * climate_factor * safety_factor
        
        # Store results
        results['flood_metrics'][column] = {
            'average_value': float(average_value),
            'std_dev': float(std_dev),
            'result_ratio': float(result),
            'flood_discharge': float(flood_discharge),
            'deviated_flood_discharge': float(deviated_flood_discharge),
            'dimensioned_flood_discharge': float(dimensioned_flood_discharge),
            'dimensioned_deviated_flood_discharge': float(dimensioned_deviated_flood_discharge)
        }
    
    # Convert NumPy types to native Python types for JSON serialization
    for station in results['filtered_stations']:
        for key, value in station.items():
            if isinstance(value, (np.int64, np.float64)):
                station[key] = float(value) if isinstance(value, np.float64) else int(value)
    
    # Create datasets for charts
    results['chart_data'] = {
        'stations': {
            'labels': [f"{s['stationName']} ({s['stationNumber']})" for s in results['filtered_stations']],
            'distances': [s['distance_to_user'] for s in results['filtered_stations']],
            'weights': [s['locality_weight_normalized'] for s in results['filtered_stations']],
            'specific_discharge': [s['specificDischarge'] for s in results['filtered_stations']]
        },
        'flood_metrics': {
            'labels': list(results['flood_metrics'].keys()),
            'flood_discharge': [metrics['flood_discharge'] for metrics in results['flood_metrics'].values()],
            'dimensioned_flood_discharge': [metrics['dimensioned_flood_discharge'] for metrics in results['flood_metrics'].values()],
            'deviated_flood_discharge': [metrics['deviated_flood_discharge'] for metrics in results['flood_metrics'].values()],
            'dimensioned_deviated_flood_discharge': [metrics['dimensioned_deviated_flood_discharge'] for metrics in results['flood_metrics'].values()]
        }
    }
    
    return results
