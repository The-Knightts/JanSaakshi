"""
Seed JanSaakshi with multi-city data.
Run: python seed_data.py
"""

import sqlite3, os
from datetime import datetime
from utils.database import init_database, create_user, DATABASE_PATH

def seed():
    # Clear existing tables
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    for table in ["follow_ups", "complaints", "meetings", "projects", "wards", "users"]:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
    conn.close()
    print("Cleared existing tables")

    init_database()
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    # ==================== USERS ====================
    create_user("user1", "pass1", "Citizen One", "mumbai", "R/S", "user")
    create_user("user2", "pass2", "Citizen Two", "delhi", None, "user")
    create_user("admin", "admin123", "Admin", "mumbai", None, "admin")
    print("Users created: user1, user2, admin")

    # ==================== MUMBAI PROJECTS ====================
    mumbai_projects = [
        # Kandivali West
        ("Kandivali West Road Resurfacing", "Resurfacing of internal roads in Kandivali West from Mahavir Nagar to Charkop. Covers 4.2 km of pothole-ridden roads with concrete overlay.", "R/S", "Kandivali West", 32000000, "Shri Bhalchandra Shirsat", "ABC Infra Pvt Ltd", "2024-05-01", "2025-05-01", "roads", "delayed", 290, "Mahavir Nagar to Charkop, Kandivali West"),
        ("Charkop Sector 8 Water Pipeline", "Replacement of old cast iron water pipelines in Charkop Sector 8. New HDPE pipes to improve pressure and reduce leakage by 60%.", "R/S", "Kandivali West", 18000000, "Shri Bhalchandra Shirsat", "HydroFix Solutions", "2024-07-15", "2025-01-15", "water_supply", "delayed", 399, "Charkop Sector 8, Kandivali West"),
        ("Poisar River Cleaning Phase 2", "De-silting and beautification of Poisar River stretch through Kandivali West. Includes embankment repair and debris removal.", "R/S", "Kandivali West", 45000000, "Shri Bhalchandra Shirsat", "CleanStream Corp", "2024-03-01", "2025-06-01", "drainage", "ongoing", 0, "Poisar River, Kandivali West section"),
        ("Mahavir Nagar Garden Upgrade", "Renovation of Mahavir Nagar public garden with new walkway, children's area, senior citizen corner, and LED lighting.", "R/S", "Kandivali West", 8500000, "Shri Bhalchandra Shirsat", "Green Spaces India", "2024-09-01", "2025-03-01", "parks", "completed", 0, "Mahavir Nagar, Kandivali West"),
        ("Charkop LED Street Lighting", "Installation of 320 new LED streetlights in Charkop Sectors 2-9. Replacing defunct mercury lights for better safety.", "R/S", "Kandivali West", 6200000, "Shri Bhalchandra Shirsat", "Bajaj Electricals", "2024-08-01", "2025-02-01", "street_lighting", "completed", 0, "Charkop Sectors 2-9, Kandivali West"),

        # Kandivali East
        ("Kandivali East STP Expansion", "Expansion of sewage treatment plant capacity from 20 MLD to 35 MLD. New secondary treatment unit and sludge drying beds.", "R/S", "Kandivali East", 120000000, "Shri Bhalchandra Shirsat", "Enviro Treatment Systems", "2023-12-01", "2025-06-01", "drainage", "delayed", 263, "Kandivali East STP, near Thakur Village"),
        ("Thakur Village Footpath Construction", "Building 2.8 km of new paver-block footpaths along Thakur Village main road. Includes tactile tiles for visually impaired.", "R/S", "Kandivali East", 14000000, "Shri Bhalchandra Shirsat", "Patel Construction", "2024-06-15", "2025-04-15", "roads", "ongoing", 0, "Thakur Village Main Road, Kandivali East"),
        ("Lokhandwala Complex Community Hall", "Construction of new 500-capacity community hall with AV equipment, kitchen, and parking for 40 vehicles.", "R/S", "Kandivali East", 28000000, "Shri Bhalchandra Shirsat", "Shree Construction Co", "2024-04-01", "2025-10-01", "other", "ongoing", 0, "Lokhandwala Complex, Kandivali East"),
        ("BMC School No.7 Renovation", "Complete renovation of BMC Primary School No.7 including new classrooms, toilets, playground surfacing, and boundary wall.", "R/S", "Kandivali East", 16000000, "Shri Bhalchandra Shirsat", "EduBuild India", "2024-08-15", "2025-06-15", "schools", "ongoing", 0, "Samata Nagar, Kandivali East"),

        # Other Mumbai wards (existing)
        ("Andheri-Kurla Road Widening", "Widening from 4 to 6 lanes to reduce traffic congestion. New footpaths and streetlights.", "K/E", "Andheri East", 45000000, "Smt. Rajul Patel", "Patel Infrastructure Ltd", "2024-06-15", "2025-06-15", "roads", "delayed", 245, "Andheri-Kurla Road, MIDC to WEH"),
        ("Bandra Water Pipeline Replacement", "Replacing 40-year-old corroded pipelines. New pipes to improve pressure and reduce leakage.", "H/W", "Bandra West", 28000000, "Shri Asif Zakaria", "Aquapure Systems", "2024-08-10", "2025-08-10", "water_supply", "ongoing", 0, "Hill Road to Linking Road, Bandra West"),
        ("Dadar Garden Renovation", "Complete renovation of Shivaji Park garden. New walking tracks, play area, seating, open gym.", "G/N", "Dadar", 12000000, "Shri Vishwanath Mahadeshwar", "Green Spaces India", "2024-04-20", "2024-12-20", "parks", "completed", 0, "Shivaji Park, Dadar West"),
        ("Malad Storm Water Drain", "New storm water drains in Malad East to prevent monsoon flooding. 3.5 km coverage.", "P/N", "Malad", 65000000, "Shri Vinod Shelar", "Nirmal Infrastructure", "2024-03-01", "2025-03-01", "drainage", "delayed", 355, "Kurar Village to Malad Station"),
        ("Worli Seaface Promenade Repair", "Repairing damaged promenade. New railings, repaving, improved drainage.", "G/S", "Worli", 35000000, "Shri Sunil Prabhu", "Marine Works India", "2024-05-10", "2025-05-10", "roads", "delayed", 280, "Haji Ali to Worli Fort"),
        ("Mulund Healthcare Centre Upgrade", "Upgrading dispensary to 30-bed centre. OPD, pathology lab, emergency ward.", "T", "Mulund", 52000000, "Shri Mihir Kotecha", "Mediquip Healthcare", "2024-01-15", "2025-01-15", "healthcare", "delayed", 400, "Mulund West, near station"),
        ("Kurla Flyover Construction", "Four-lane, 1.2 km flyover at Kurla junction. LBS Marg to CST Road.", "L", "Kurla", 180000000, "Shri Mangesh Kudalkar", "L&T Infrastructure", "2023-09-01", "2025-09-01", "roads", "ongoing", 0, "Kurla Junction, LBS Marg"),
        ("Borivali School Extension", "Adding 8 classrooms and computer lab to BMC School No.4. 320 more students.", "R/C", "Borivali", 18000000, "Smt. Sandya Doshi", "Shree Construction Co", "2024-07-15", "2025-07-15", "schools", "ongoing", 0, "LIC Colony, Borivali West"),
        ("Ghatkopar LED Lights", "Replacing 450 mercury streetlights with LED. 40% electricity savings.", "N", "Ghatkopar", 8500000, "Shri Pravin Darekar", "Bajaj Electricals", "2024-09-01", "2025-03-01", "street_lighting", "completed", 0, "Tilak Nagar to Pant Nagar"),
        ("Colaba Heritage Walk", "Heritage walk trail with information boards, cobblestone paths, street furniture.", "A", "Colaba", 15000000, "Shri Makrand Narwekar", "Heritage Craft Studios", "2024-11-01", "2025-11-01", "other", "approved", 0, "Colaba Causeway to Gateway of India"),
        ("Byculla Zoo Road Resurfacing", "Resurfacing road around Rani Baugh. New crossing signals and footpath repairs.", "E", "Byculla", 22000000, "Shri Rais Shaikh", "Roadmaster Constructions", "2024-06-01", "2024-12-01", "roads", "delayed", 445, "Dr. Ambedkar Road, Byculla"),
    ]

    for p in mumbai_projects:
        cursor.execute("""
            INSERT INTO projects (city, project_name, summary, ward_number, ward_name,
                budget_amount, corporator_name, contractor_name, approval_date,
                expected_completion, project_type, status, delay_days, location_details,
                source_pdf, extracted_at, created_at)
            VALUES ('mumbai',?,?,?,?,?,?,?,?,?,?,?,?,?,'seed_data',?,?)
        """, (*p, now, now))

    print(f"Mumbai: {len(mumbai_projects)} projects seeded")

    # ==================== DELHI PROJECTS ====================
    delhi_projects = [
        ("Chandni Chowk Street Redesign Phase 3", "Pedestrianization and beautification of remaining Chandni Chowk sections. Underground cabling, new stone paving, drainage.", "Central", "Chandni Chowk", 85000000, "MCD Commissioner", "Shapoorji Pallonji", "2024-02-01", "2025-06-01", "roads", "delayed", 263, "Chandni Chowk Main Road, Old Delhi"),
        ("Najafgarh Drain Rejuvenation", "Cleaning and widening of Najafgarh drain to prevent annual flooding. 8 km stretch near Dwarka.", "South West", "Dwarka", 150000000, "MCD South West", "Tata Projects", "2023-11-01", "2025-05-01", "drainage", "delayed", 294, "Najafgarh Drain, Dwarka Sector 12-22"),
        ("Saket District Park Renovation", "Renovation of 12-acre Saket District Park. New jogging track, amphitheatre, native plantation, solar lighting.", "South", "Saket", 22000000, "MCD South Zone", "Green Delhi Foundation", "2024-06-01", "2025-03-01", "parks", "completed", 0, "Saket District Park, Press Enclave Road"),
        ("Rohini Sector 11 Water ATMs", "Installation of 25 water ATM machines across Rohini sectors 9-16. Solar powered, RO purified.", "North West", "Rohini", 8000000, "MCD North West", "WaterLife India", "2024-10-01", "2025-04-01", "water_supply", "ongoing", 0, "Rohini Sectors 9-16"),
        ("Lajpat Nagar Market Smart Lighting", "Replacing all market area lights with smart LED poles. Motion sensors, CCTV integration.", "South", "Lajpat Nagar", 12000000, "MCD South Zone", "Crompton Greaves", "2024-08-01", "2025-02-01", "street_lighting", "completed", 0, "Lajpat Nagar Central Market"),
        ("Pitampura MCD School Upgrades", "Upgrading 5 MCD primary schools with smart classrooms, new labs, and renovated toilets.", "North West", "Pitampura", 35000000, "MCD North West", "EduBuild India", "2024-05-15", "2025-08-15", "schools", "ongoing", 0, "Pitampura Sectors 4, 7, 12, 16, 21"),
        ("Okhla Waste-to-Energy Plant Expansion", "Adding 1000 TPD capacity to Okhla waste processing. New emission control systems.", "South East", "Okhla", 200000000, "MCD South East", "Jindal Urban Infra", "2023-08-01", "2025-08-01", "waste_management", "delayed", 204, "Okhla Industrial Area Phase 2"),
        ("Janakpuri District Road Widening", "Widening C-2 block main road from 2 lanes to 4 lanes. New divider, footpaths, bus bays.", "West", "Janakpuri", 42000000, "MCD West Zone", "NBCC India Ltd", "2024-04-01", "2025-04-01", "roads", "delayed", 325, "C-2 Block Main Road, Janakpuri"),
        ("Karol Bagh Pedestrian Plaza", "Creating car-free zone in Ajmal Khan Road area. New seating, tree plantation, vendor zones.", "Central", "Karol Bagh", 30000000, "MCD Central", "PWD Delhi", "2024-07-01", "2025-07-01", "other", "ongoing", 0, "Ajmal Khan Road, Karol Bagh"),
        ("Mayur Vihar Health Centre", "New 50-bed polyclinic with diagnostics, dental unit, eye care, and pharmacy for East Delhi residents.", "East", "Mayur Vihar", 65000000, "MCD East Zone", "Delhi Health Infra", "2024-01-01", "2025-06-01", "healthcare", "delayed", 263, "Mayur Vihar Phase 1, Pocket 2"),
        ("Dwarka Sector 21 Metro Connectivity Road", "Last-mile road connecting Dwarka Sec 21 Metro to residential areas. 1.5 km with cycle track.", "South West", "Dwarka", 25000000, "MCD South West", "Delhi PWD", "2024-09-01", "2025-09-01", "roads", "ongoing", 0, "Dwarka Sector 21 Metro Station area"),
        ("Shahdara Nallah Covering", "Covering 2.3 km of open nallah through Shahdara. Road construction on top for traffic relief.", "Shahdara", "Shahdara", 75000000, "MCD Shahdara", "Gammon India", "2024-03-01", "2025-09-01", "drainage", "ongoing", 0, "GT Road to Shahdara Railway Station"),
    ]

    for p in delhi_projects:
        cursor.execute("""
            INSERT INTO projects (city, project_name, summary, ward_number, ward_name,
                budget_amount, corporator_name, contractor_name, approval_date,
                expected_completion, project_type, status, delay_days, location_details,
                source_pdf, extracted_at, created_at)
            VALUES ('delhi',?,?,?,?,?,?,?,?,?,?,?,?,?,'seed_data',?,?)
        """, (*p, now, now))

    print(f"Delhi: {len(delhi_projects)} projects seeded")

    # ==================== MUMBAI MEETINGS ====================
    mumbai_meetings = [
        ("R/S", "Kandivali", "2025-01-15", "ward_committee", "Kandivali Ward Office, S.V. Road", "Review of ongoing infrastructure projects in Kandivali East and West", "Corporator Shirsat, AE Roads, AE Water, 12 citizens", "Charkop Water Pipeline, Thakur Village Footpath, STP Expansion"),
        ("R/S", "Kandivali", "2024-11-20", "ward_committee", "Kandivali Ward Office", "Pre-monsoon drain cleaning and road maintenance discussion", "Corporator Shirsat, Ward Officer, Storm Water Dept, 8 citizens", "Poisar River Cleaning, Mahavir Nagar Garden"),
        ("K/E", "Andheri East", "2025-01-10", "ward_committee", "K/E Ward Office, MIDC", "Road widening project progress review and traffic management", "Corporator Patel, Traffic Police, PWD, 15 citizens", "Andheri-Kurla Road Widening"),
        ("G/N", "Dadar", "2024-12-05", "ward_committee", "Shivaji Park Office", "Garden renovation completion and maintenance planning", "Corporator Mahadeshwar, Garden Dept, 10 citizens", "Dadar Garden Renovation"),
        ("T", "Mulund", "2025-02-01", "ward_committee", "Mulund Ward Office", "Healthcare centre construction delay review and action plan", "Corporator Kotecha, Health Dept, Contractor Rep, 20 citizens", "Mulund Healthcare Centre Upgrade"),
    ]

    for m in mumbai_meetings:
        cursor.execute("""
            INSERT INTO meetings (city, ward_number, ward_name, meeting_date, meeting_type, venue, objective, attendees, projects_discussed)
            VALUES ('mumbai',?,?,?,?,?,?,?,?)
        """, m)

    # ==================== DELHI MEETINGS ====================
    delhi_meetings = [
        ("Central", "Chandni Chowk", "2025-01-20", "zone_committee", "MCD Central Office, Daryaganj", "Chandni Chowk Phase 3 progress and vendor relocation plan", "MCD Commissioner, Zone Chair, Traffic Police, 25 traders", "Chandni Chowk Street Redesign"),
        ("South West", "Dwarka", "2025-01-08", "zone_committee", "MCD Dwarka Zone Office", "Najafgarh drain flooding review and monsoon preparedness", "Zone Chair, Irrigation Dept, DDA, 30 citizens", "Najafgarh Drain Rejuvenation, Dwarka Metro Road"),
        ("North West", "Rohini", "2024-12-15", "zone_committee", "MCD Rohini Zone Office", "School upgrades progress and water ATM installation status", "Zone Chair, Education Dept, Water Board, 15 citizens", "Pitampura School Upgrades, Rohini Water ATMs"),
        ("East", "Mayur Vihar", "2025-02-05", "zone_committee", "MCD East Zone Office", "Health centre delay and Shahdara nallah covering update", "Zone Chair, Health Dept, Contractor Reps, 18 citizens", "Mayur Vihar Health Centre, Shahdara Nallah Covering"),
    ]

    for m in delhi_meetings:
        cursor.execute("""
            INSERT INTO meetings (city, ward_number, ward_name, meeting_date, meeting_type, venue, objective, attendees, projects_discussed)
            VALUES ('delhi',?,?,?,?,?,?,?,?)
        """, m)

    print(f"Meetings: {len(mumbai_meetings)} Mumbai + {len(delhi_meetings)} Delhi seeded")

    conn.commit()
    conn.close()
    print(f"\nDone! Total: {len(mumbai_projects)} Mumbai + {len(delhi_projects)} Delhi projects, {len(mumbai_meetings)+len(delhi_meetings)} meetings, 3 users")


if __name__ == "__main__":
    seed()