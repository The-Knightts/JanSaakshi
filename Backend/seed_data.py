"""Seed JanSaakshi multi-city data. Run: python seed_data.py"""

import sqlite3, os
from datetime import datetime
from utils.database import init_database, create_user, DATABASE_PATH


def seed():
    # Delete DB file to avoid lock issues
    if os.path.exists(DATABASE_PATH):
        try:
            os.remove(DATABASE_PATH)
            print(f"Deleted {DATABASE_PATH}")
        except PermissionError:
            print(f"ERROR: {DATABASE_PATH} is locked. Stop the Flask server first (Ctrl+C), then re-run.")
            return

    init_database()
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    c = conn.cursor()
    now = datetime.now().isoformat()

    # ==================== CITIES ====================
    c.execute("INSERT INTO city (city_name, state) VALUES ('mumbai', 'Maharashtra')")
    mumbai_id = c.lastrowid
    c.execute("INSERT INTO city (city_name, state) VALUES ('delhi', 'Delhi')")
    delhi_id = c.lastrowid
    conn.commit()
    print(f"Cities: mumbai={mumbai_id}, delhi={delhi_id}")

    # ==================== USERS ====================
    conn.commit()
    conn.close()
    create_user("user1", "pass1", "Citizen One", city_id=mumbai_id, ward="77", role="user")
    create_user("user2", "pass2", "Citizen Two", city_id=delhi_id, ward=None, role="user")
    create_user("admin", "admin123", "Admin", city_id=mumbai_id, ward=None, role="admin")
    print("Users: user1, user2, admin")
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    c = conn.cursor()

    # ==================== MUMBAI PROJECTS ====================
    # ward_no = actual BMC ward number, ward_zone = zone code for hover
    mumbai = [
        # Kandivali West (Ward 77, Zone R/S)
        ("Kandivali West Road Resurfacing", "Resurfacing of internal roads from Mahavir Nagar to Charkop, covering 4.2 km of pothole-ridden roads with concrete overlay.", "77", "Kandivali West", "R/S", "delayed", 32000000, "Shri Bhalchandra Shirsat", "ABC Infra Pvt Ltd", "roads", "2024-05-01", "2024-06-01", "2025-05-01", None, 290, "Mahavir Nagar to Charkop"),
        ("Charkop Sector 8 Water Pipeline", "Replacement of old cast iron water pipelines with HDPE pipes to improve pressure and reduce leakage by 60%.", "77", "Kandivali West", "R/S", "delayed", 18000000, "Shri Bhalchandra Shirsat", "HydroFix Solutions", "water_supply", "2024-07-15", "2024-08-01", "2025-01-15", None, 399, "Charkop Sector 8"),
        ("Poisar River Cleaning Phase 2", "De-silting and beautification of Poisar River stretch. Embankment repair and debris removal.", "77", "Kandivali West", "R/S", "ongoing", 45000000, "Shri Bhalchandra Shirsat", "CleanStream Corp", "drainage", "2024-03-01", "2024-04-01", "2025-06-01", None, 0, "Poisar River, Kandivali West"),
        ("Mahavir Nagar Garden Upgrade", "Renovation with new walkway, children's area, senior citizen corner, and LED lighting.", "77", "Kandivali West", "R/S", "completed", 8500000, "Shri Bhalchandra Shirsat", "Green Spaces India", "parks", "2024-09-01", "2024-10-01", "2025-03-01", "2025-02-15", 0, "Mahavir Nagar"),
        ("Charkop LED Street Lighting", "Installation of 320 new LED streetlights in Charkop Sectors 2-9 replacing defunct mercury lights.", "77", "Kandivali West", "R/S", "completed", 6200000, "Shri Bhalchandra Shirsat", "Bajaj Electricals", "street_lighting", "2024-08-01", "2024-09-01", "2025-02-01", "2025-01-20", 0, "Charkop Sectors 2-9"),

        # Kandivali East (Ward 78, Zone R/S)
        ("Kandivali East STP Expansion", "Expansion of sewage treatment plant from 20 MLD to 35 MLD. New secondary treatment unit.", "78", "Kandivali East", "R/S", "delayed", 120000000, "Shri Bhalchandra Shirsat", "Enviro Treatment Systems", "drainage", "2023-12-01", "2024-02-01", "2025-06-01", None, 263, "Thakur Village STP"),
        ("Thakur Village Footpath Construction", "Building 2.8 km of paver-block footpaths with tactile tiles for visually impaired.", "78", "Kandivali East", "R/S", "ongoing", 14000000, "Shri Bhalchandra Shirsat", "Patel Construction", "roads", "2024-06-15", "2024-07-15", "2025-04-15", None, 0, "Thakur Village Main Road"),
        ("Lokhandwala Community Hall", "New 500-capacity community hall with AV equipment, kitchen, parking for 40 vehicles.", "78", "Kandivali East", "R/S", "ongoing", 28000000, "Shri Bhalchandra Shirsat", "Shree Construction", "other", "2024-04-01", "2024-05-01", "2025-10-01", None, 0, "Lokhandwala Complex"),
        ("BMC School No.7 Renovation", "Complete renovation: new classrooms, toilets, playground surfacing, boundary wall.", "78", "Kandivali East", "R/S", "ongoing", 16000000, "Shri Bhalchandra Shirsat", "EduBuild India", "schools", "2024-08-15", "2024-09-15", "2025-06-15", None, 0, "Samata Nagar"),

        # Andheri East (Ward 69, Zone K/E)
        ("Andheri-Kurla Road Widening", "Widening from 4 to 6 lanes for traffic relief. New footpaths and streetlights.", "69", "Andheri East", "K/E", "delayed", 45000000, "Smt. Rajul Patel", "Patel Infrastructure", "roads", "2024-06-15", "2024-07-15", "2025-06-15", None, 245, "MIDC to WEH"),
        # Andheri West (Ward 68, Zone K/W)
        ("Versova Beach Promenade", "New 1.2 km seaside promenade with jogging track, seating, public art installations.", "68", "Andheri West", "K/W", "ongoing", 38000000, "Shri Ameet Satam", "Marine Works India", "parks", "2024-10-01", "2024-11-01", "2025-10-01", None, 0, "Versova Beach"),

        # Bandra West (Ward 64, Zone H/W)
        ("Bandra Water Pipeline Replacement", "Replacing 40-year-old corroded pipelines. New pipes for better pressure.", "64", "Bandra West", "H/W", "ongoing", 28000000, "Shri Asif Zakaria", "Aquapure Systems", "water_supply", "2024-08-10", "2024-09-10", "2025-08-10", None, 0, "Hill Road to Linking Road"),

        # Dadar (Ward 40, Zone G/N)
        ("Shivaji Park Garden Renovation", "New walking tracks, play area, seating, open gym installations.", "40", "Dadar", "G/N", "completed", 12000000, "Shri Vishwanath Mahadeshwar", "Green Spaces India", "parks", "2024-04-20", "2024-05-20", "2024-12-20", "2024-12-15", 0, "Shivaji Park"),

        # Malad (Ward 75, Zone P/N)
        ("Malad Storm Water Drain", "New storm water drains to prevent monsoon flooding. 3.5 km coverage.", "75", "Malad", "P/N", "delayed", 65000000, "Shri Vinod Shelar", "Nirmal Infrastructure", "drainage", "2024-03-01", "2024-04-01", "2025-03-01", None, 355, "Kurar Village to Malad Station"),

        # Worli (Ward 54, Zone G/S)
        ("Worli Seaface Promenade Repair", "Repairing damaged promenade. New railings, repaving, drainage improvement.", "54", "Worli", "G/S", "delayed", 35000000, "Shri Sunil Prabhu", "Marine Works India", "roads", "2024-05-10", "2024-06-10", "2025-05-10", None, 280, "Haji Ali to Worli Fort"),

        # Mulund (Ward 85, Zone T)
        ("Mulund Healthcare Centre Upgrade", "Upgrading dispensary to 30-bed centre. OPD, pathology lab, emergency ward.", "85", "Mulund", "T", "delayed", 52000000, "Shri Mihir Kotecha", "Mediquip Healthcare", "healthcare", "2024-01-15", "2024-03-01", "2025-01-15", None, 400, "Mulund West, near station"),

        # Kurla (Ward 61, Zone L)
        ("Kurla Flyover Construction", "Four-lane 1.2 km flyover at Kurla junction. LBS Marg to CST Road.", "61", "Kurla", "L", "ongoing", 180000000, "Shri Mangesh Kudalkar", "L&T Infrastructure", "roads", "2023-09-01", "2024-01-01", "2025-09-01", None, 0, "LBS Marg Junction"),

        # Borivali (Ward 80, Zone R/C)
        ("Borivali School Extension", "Adding 8 classrooms and computer lab. 320 more student capacity.", "80", "Borivali", "R/C", "ongoing", 18000000, "Smt. Sandya Doshi", "Shree Construction", "schools", "2024-07-15", "2024-08-15", "2025-07-15", None, 0, "LIC Colony"),

        # Ghatkopar (Ward 72, Zone N)
        ("Ghatkopar LED Street Lights", "Replacing 450 mercury streetlights with LED. 40% electricity savings.", "72", "Ghatkopar", "N", "completed", 8500000, "Shri Pravin Darekar", "Bajaj Electricals", "street_lighting", "2024-09-01", "2024-10-01", "2025-03-01", "2025-02-28", 0, "Tilak Nagar to Pant Nagar"),
    ]

    for p in mumbai:
        c.execute("""
            INSERT INTO projects (city_id, project_name, summary, ward_no, ward_name, ward_zone,
                status, budget, corporator_name, contractor_name, project_type,
                approval_date, start_date, expected_completion, actual_completion,
                delay_days, location_details, source_pdf, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'seed_data',?,?)
        """, (mumbai_id, *p, now, now))

    print(f"Mumbai: {len(mumbai)} projects")

    # ==================== DELHI PROJECTS ====================
    delhi = [
        ("Chandni Chowk Street Redesign Phase 3", "Pedestrianization and beautification. Underground cabling, stone paving, drainage.", "1", "Chandni Chowk", "Central", "delayed", 85000000, "MCD Commissioner", "Shapoorji Pallonji", "roads", "2024-02-01", "2024-04-01", "2025-06-01", None, 263, "Chandni Chowk Main Road"),
        ("Najafgarh Drain Rejuvenation", "Cleaning and widening to prevent flooding. 8 km stretch near Dwarka.", "50", "Dwarka", "South West", "delayed", 150000000, "MCD South West", "Tata Projects", "drainage", "2023-11-01", "2024-01-01", "2025-05-01", None, 294, "Sector 12-22"),
        ("Saket District Park Renovation", "12-acre park renovation. Jogging track, amphitheatre, native plantation, solar lighting.", "120", "Saket", "South", "completed", 22000000, "MCD South Zone", "Green Delhi Foundation", "parks", "2024-06-01", "2024-07-01", "2025-03-01", "2025-02-20", 0, "Press Enclave Road"),
        ("Rohini Water ATMs", "25 solar-powered RO water ATMs across Rohini sectors 9-16.", "30", "Rohini", "North West", "ongoing", 8000000, "MCD North West", "WaterLife India", "water_supply", "2024-10-01", "2024-11-01", "2025-04-01", None, 0, "Sectors 9-16"),
        ("Lajpat Nagar Smart Lighting", "Smart LED poles in market area. Motion sensors, CCTV integration.", "108", "Lajpat Nagar", "South", "completed", 12000000, "MCD South Zone", "Crompton Greaves", "street_lighting", "2024-08-01", "2024-09-01", "2025-02-01", "2025-01-25", 0, "Central Market"),
        ("Pitampura MCD School Upgrades", "Upgrading 5 MCD primary schools with smart classrooms, labs, renovated toilets.", "35", "Pitampura", "North West", "ongoing", 35000000, "MCD North West", "EduBuild India", "schools", "2024-05-15", "2024-07-01", "2025-08-15", None, 0, "Sectors 4, 7, 12, 16, 21"),
        ("Okhla Waste-to-Energy Expansion", "Adding 1000 TPD capacity. New emission control systems.", "130", "Okhla", "South East", "delayed", 200000000, "MCD South East", "Jindal Urban Infra", "waste_management", "2023-08-01", "2023-10-01", "2025-08-01", None, 204, "Industrial Area Phase 2"),
        ("Janakpuri Road Widening", "Widening C-2 block road from 2 to 4 lanes. Divider, footpaths, bus bays.", "68", "Janakpuri", "West", "delayed", 42000000, "MCD West Zone", "NBCC India Ltd", "roads", "2024-04-01", "2024-06-01", "2025-04-01", None, 325, "C-2 Block Main Road"),
        ("Karol Bagh Pedestrian Plaza", "Car-free zone on Ajmal Khan Road. Seating, tree plantation, vendor zones.", "5", "Karol Bagh", "Central", "ongoing", 30000000, "MCD Central", "PWD Delhi", "other", "2024-07-01", "2024-08-01", "2025-07-01", None, 0, "Ajmal Khan Road"),
        ("Mayur Vihar Health Centre", "New 50-bed polyclinic with diagnostics, dental, eye care, pharmacy.", "150", "Mayur Vihar", "East", "delayed", 65000000, "MCD East Zone", "Delhi Health Infra", "healthcare", "2024-01-01", "2024-03-01", "2025-06-01", None, 263, "Phase 1, Pocket 2"),
        ("Dwarka Metro Connectivity Road", "Last-mile road connecting Sec 21 Metro to residences. 1.5 km with cycle track.", "52", "Dwarka", "South West", "ongoing", 25000000, "MCD South West", "Delhi PWD", "roads", "2024-09-01", "2024-10-01", "2025-09-01", None, 0, "Sector 21 Metro area"),
        ("Shahdara Nallah Covering", "Covering 2.3 km open nallah. Road construction on top for traffic relief.", "80", "Shahdara", "Shahdara", "ongoing", 75000000, "MCD Shahdara", "Gammon India", "drainage", "2024-03-01", "2024-05-01", "2025-09-01", None, 0, "GT Road to Railway Station"),
    ]

    for p in delhi:
        c.execute("""
            INSERT INTO projects (city_id, project_name, summary, ward_no, ward_name, ward_zone,
                status, budget, corporator_name, contractor_name, project_type,
                approval_date, start_date, expected_completion, actual_completion,
                delay_days, location_details, source_pdf, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'seed_data',?,?)
        """, (delhi_id, *p, now, now))

    print(f"Delhi: {len(delhi)} projects")

    # ==================== MUMBAI MEETINGS ====================
    mumbai_meetings = [
        ("77", "Kandivali", "2025-01-15", "ward_committee", "Kandivali Ward Office, S.V. Road", "Review of ongoing infrastructure projects in Kandivali East and West", "Corporator Shirsat, AE Roads, AE Water, 12 citizens", '["Charkop Water Pipeline", "Thakur Village Footpath", "STP Expansion"]', None, 3),
        ("77", "Kandivali", "2024-11-20", "ward_committee", "Kandivali Ward Office", "Pre-monsoon drain cleaning and road maintenance", "Corporator Shirsat, Ward Officer, Storm Water Dept, 8 citizens", '["Poisar River Cleaning", "Mahavir Nagar Garden"]', None, 2),
        ("69", "Andheri East", "2025-01-10", "ward_committee", "K/E Ward Office, MIDC", "Road widening project progress and traffic management", "Corporator Patel, Traffic Police, PWD, 15 citizens", '["Andheri-Kurla Road Widening"]', None, 1),
        ("40", "Dadar", "2024-12-05", "ward_committee", "Shivaji Park Office", "Garden renovation completion and maintenance planning", "Corporator Mahadeshwar, Garden Dept, 10 citizens", '["Shivaji Park Garden Renovation"]', None, 1),
        ("85", "Mulund", "2025-02-01", "ward_committee", "Mulund Ward Office", "Healthcare centre delay review and action plan", "Corporator Kotecha, Health Dept, Contractor Rep, 20 citizens", '["Mulund Healthcare Centre Upgrade"]', None, 1),
    ]

    for m in mumbai_meetings:
        c.execute("""
            INSERT INTO meetings (city_id, ward_no, ward_name, meet_date, meet_type, venue, objective, attendees, projects_discussed, source_pdf, project_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (mumbai_id, *m))

    # ==================== DELHI MEETINGS ====================
    delhi_meetings = [
        ("1", "Chandni Chowk", "2025-01-20", "zone_committee", "MCD Central Office, Daryaganj", "Phase 3 progress and vendor relocation plan", "Commissioner, Zone Chair, Traffic Police, 25 traders", '["Chandni Chowk Street Redesign"]', None, 1),
        ("50", "Dwarka", "2025-01-08", "zone_committee", "MCD Dwarka Zone Office", "Drain flooding review and monsoon preparedness", "Zone Chair, Irrigation, DDA, 30 citizens", '["Najafgarh Drain Rejuvenation", "Dwarka Metro Road"]', None, 2),
        ("30", "Rohini", "2024-12-15", "zone_committee", "MCD Rohini Zone Office", "School upgrades and water ATM installation status", "Zone Chair, Education, Water Board, 15 citizens", '["Pitampura School Upgrades", "Rohini Water ATMs"]', None, 2),
        ("150", "Mayur Vihar", "2025-02-05", "zone_committee", "MCD East Zone Office", "Health centre delay and nallah covering update", "Zone Chair, Health Dept, Contractors, 18 citizens", '["Mayur Vihar Health Centre", "Shahdara Nallah Covering"]', None, 2),
    ]

    for m in delhi_meetings:
        c.execute("""
            INSERT INTO meetings (city_id, ward_no, ward_name, meet_date, meet_type, venue, objective, attendees, projects_discussed, source_pdf, project_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (delhi_id, *m))

    print(f"Meetings: {len(mumbai_meetings)} Mumbai + {len(delhi_meetings)} Delhi")

    conn.commit()
    conn.close()
    print(f"\nDone! {len(mumbai)} Mumbai + {len(delhi)} Delhi projects, {len(mumbai_meetings)+len(delhi_meetings)} meetings, 3 users")


if __name__ == "__main__":
    seed()