from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
import math
import csv

# Initialize Flask app
app = Flask(__name__)

# Configuration for SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Charity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    charity_name = db.Column(db.String(100), nullable=False)
    place_name = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    vulnerability = db.Column(db.String(50), nullable=True)  # New column for vulnerability

# Mapping of charity names to vulnerabilities
vulnerability_mapping = {
    "Financial Hardship": [
        "Money Helper", "Citizens Advice", "Step Change Debt Charity",
        "National debtline", "Mind", "National Gambling helpline",
        "Gamblers Anonymoys UK", "Gamble Aware", "GamCare", "Gam-Anon", "GAMSTOP"
    ],
    "Low Literacy": [
        "Alzheimers society","alzheimer's Society","alzheimer's Society" "Age UK", "Dementia UK", "National Gambling Helpline",
        "Gamblers Anonymous UK", "Gamble Aware", "GamCare", "Gam-Anon", "GAMSTOP",
        "CarersUK","carers UK","carers UK","Citizens Advice"
    ],
    "Physical": ["Alzheimers society", "Age UK", "Dementia UK", "NHS"],
    "Mental": [
        "Mind", "Hestia", "Refuge", "Samaritans", "Turn2Us", "GAMSTOP", "Gam-Anon",
        "GamCare", "Gamble Aware", "Gamblers Anonymous UK", "National Debtline",
        "Step Change debt charity"
    ]
}

# Helper function to calculate distance (Haversine formula)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_charities():
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid latitude or longitude."}), 400

    vulnerability_filter = request.args.get('vulnerability')
    charities_query = Charity.query

    if vulnerability_filter:
        charities_query = charities_query.filter(Charity.vulnerability.in_(vulnerability_filter.split(',')))

    charities = charities_query.all()
    results = []

    seen = set()  # Track unique charities
    for charity in charities:
        unique_key = (charity.charity_name, charity.address, charity.vulnerability)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        distance = calculate_distance(latitude, longitude, charity.latitude, charity.longitude)
        if distance <= 30:  # Distance threshold
            results.append({
                'id': charity.id,
                'charity_name': charity.charity_name,
                'place_name': charity.place_name,
                'address': charity.address,
                'phone_number': charity.phone_number,
                'latitude': charity.latitude,
                'longitude': charity.longitude,
                'vulnerability': charity.vulnerability,
                'distance': round(distance, 2)
            })

    results.sort(key=lambda x: x['distance'])
    return jsonify(results)

def load_data():
    # Load data from CSV file into the database
    with open('charities_near_knutsford.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            charity = Charity(
                charity_name=row['Charity Name'],
                place_name=row['Place Name'],
                latitude=float(row['Latitude']),
                longitude=float(row['Longitude']),
                address=row['Address'],
                phone_number=row['Phone Number']
            )
            db.session.add(charity)
        db.session.commit()

def populate_vulnerability():
    # Populate the vulnerability column based on the mapping
    charities = Charity.query.all()
    unmapped_charities = []

    for charity in charities:
        mapped = False
        for vulnerability, names in vulnerability_mapping.items():
            # Check for exact match ignoring case and leading/trailing spaces
            if charity.charity_name.strip().lower() in [name.strip().lower() for name in names]:
                charity.vulnerability = vulnerability
                mapped = True
                break  # Stop once a match is found
        if not mapped:
            unmapped_charities.append(charity.charity_name)
    
    db.session.commit()
    
    if unmapped_charities:
        print("The following charities could not be mapped to vulnerabilities:")
        print("\n".join(unmapped_charities))
    else:
        print("Vulnerability column populated successfully!")


if __name__ == '__main__':
    # Initialize the database
    with app.app_context():
        db.create_all()
        load_data()  # Load initial data
        populate_vulnerability()  # Populate vulnerability column
    app.run(debug=True)
