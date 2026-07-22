from pymongo import MongoClient

client = MongoClient("mongodb+srv://progixtechnology_db_user:mmEgsNkhpORYA345@cluster0.hqkvaho.mongodb.net/?appName=Cluster0")
db = client["leadgen_pro"]
collection = db["automation_settings"]

categories = [
    "Roofing Contractors", "Commercial Roofing", "Roof Repair", "Roof Inspection", "Roof Replacement",
    "HVAC Services", "Commercial HVAC", "HVAC Repair", "HVAC Installation", "Air Conditioning Repair",
    "Heating Contractors", "Air Duct Cleaning", "Plumbers", "Emergency Plumbers", "Drain Cleaning",
    "Water Heater Installation", "Septic Services", "Electricians", "Emergency Electricians",
    "Electrical Contractors", "Generator Installation", "EV Charger Installation", "General Contractors",
    "Construction Companies", "Commercial Contractors", "Custom Home Builders", "Home Builders",
    "Kitchen Remodeling", "Bathroom Remodeling", "Home Remodeling", "Basement Finishing", "Home Renovation",
    "Concrete Contractors", "Concrete Repair", "Foundation Repair", "Masonry Contractors", "Stucco Contractors",
    "Deck Builders", "Fence Contractors", "Pergola Builders", "Patio Contractors", "Flooring Contractors",
    "Tile Installation", "Carpet Installation", "Hardwood Flooring", "Interior Designers", "Architectural Firms",
    "Landscape Designers", "Landscaping Services", "Lawn Care", "Tree Removal", "Tree Trimming",
    "Irrigation Services", "Pest Control", "Wildlife Removal", "Mosquito Control", "Pressure Washing",
    "Window Cleaning", "Gutter Cleaning", "Chimney Cleaning", "Water Damage Restoration",
    "Fire Damage Restoration", "Mold Remediation", "Disaster Restoration", "Garage Door Repair",
    "Garage Door Installation", "Glass Repair Services", "Window Installation", "Door Installation",
    "Swimming Pool Builders", "Pool Cleaning Services", "Pool Repair", "Pool Maintenance",
    "Solar Panel Installers", "Solar Energy Companies", "Battery Storage Installers",
    "Security Camera Installation", "Alarm System Installation", "Access Control Systems", "Home Automation",
    "Locksmiths", "Moving Companies", "Junk Removal", "Storage Facilities", "Auto Repair", "Auto Body Shops",
    "Transmission Repair", "Brake Repair", "Oil Change Services", "Tire Shops", "Wheel Alignment",
    "Windshield Repair", "Mobile Car Detailing", "Car Wash", "Car Dealerships", "Dentists", "Cosmetic Dentists",
    "Orthodontists", "Dental Implants Clinics", "Pediatric Dentists", "Emergency Dentists", "Medical Spas",
    "Med Spa Clinics", "IVF Clinics", "Dermatology Clinics", "Plastic Surgery Clinics", "Urgent Care Clinics",
    "Pediatric Clinics", "Psychology Clinics", "Psychiatrists", "Physiotherapy Clinics", "Chiropractors",
    "Speech Therapy Centers", "Occupational Therapy Centers", "Home Healthcare Services", "Weight Loss Clinics",
    "Wellness Centers", "Veterinary Clinics", "Animal Hospitals", "Pet Grooming", "Pet Boarding",
    "Personal Injury Lawyers", "Corporate Lawyers", "Immigration Lawyers", "Family Lawyers",
    "Bankruptcy Lawyers", "Criminal Defense Lawyers", "Estate Planning Lawyers", "Business Lawyers",
    "Accountants", "CPA Firms", "Tax Consultants", "Bookkeeping Services", "Payroll Services",
    "Financial Advisors", "Wealth Management", "Insurance Agencies", "Real Estate Agents",
    "Commercial Real Estate", "Mortgage Brokers", "Property Management", "Home Inspectors", "IT Support Services",
    "Managed IT Services", "Cybersecurity Consultants", "Cloud Consulting", "Software Development Companies",
    "Web Design Agencies", "SEO Agencies", "Digital Marketing Agencies", "Advertising Agencies",
    "Branding Agencies", "Marketing Consultants", "PR Agencies", "Recruitment Agencies", "Staffing Agencies",
    "HR Consulting", "Business Consultants", "Consulting Agencies", "Logistics Companies", "Freight Companies",
    "Warehousing Companies", "Courier Services", "Supply Chain Consultants", "Printing Services",
    "Signage Companies", "Packaging Companies", "Restaurants", "Coffee Shops", "Cafes", "Bakeries",
    "Cloud Kitchens", "Food Trucks", "Catering Services", "Manufacturing Companies", "Food Manufacturers",
    "Beverage Manufacturers", "Industrial Suppliers", "Machine Shops", "Metal Fabrication", "Hair Salons",
    "Barber Shops", "Nail Salons", "Beauty Clinics", "Eyelash Studios", "Tattoo Studios", "Massage Therapy",
    "Gyms", "Personal Trainers", "Pilates Studios", "Crossfit Gyms", "Yoga Studios", "Martial Arts Schools",
    "Music Schools", "Dance Schools", "Tutoring Centers", "Test Prep Centers", "Preschools", "Private Schools",
    "Daycare Centers", "Senior Care Services", "Assisted Living Facilities", "Retirement Communities",
    "Travel Agencies", "Wedding Planners", "Corporate Event Planners", "Event Management Companies",
    "Photography Studios", "Video Production Companies",
    # Food & Beverage
    "Restaurants", "Fast Food Restaurants", "Fine Dining Restaurants", "Family Restaurants", "Italian Restaurants",
    "Indian Restaurants", "Chinese Restaurants", "Mexican Restaurants", "Japanese Restaurants",
    "Thai Restaurants", "Seafood Restaurants", "Steakhouses", "Pizza Restaurants", "Burger Restaurants",
    "Sushi Restaurants", "BBQ Restaurants", "Cafes", "Coffee Shops", "Tea Houses", "Bakeries", "Cake Shops",
    "Pastry Shops", "Dessert Shops", "Ice Cream Shops", "Donut Shops", "Juice Bars", "Smoothie Bars",
    "Food Trucks", "Cloud Kitchens", "Catering Services", "Meal Prep Services", "Bars", "Sports Bars",
    "Wine Bars", "Cocktail Bars", "Breweries", "Microbreweries", "Wineries", "Hotels", "Motels", "Resorts",
    "Bed and Breakfast", "Vacation Rentals"
]

settings = collection.find_one({})
if settings:
    existing_categories = settings.get("categories", [])
    new_cats = existing_categories.copy()
    for cat in categories:
        if cat not in new_cats:
            new_cats.append(cat)
    
    collection.update_one({"_id": settings["_id"]}, {"$set": {"categories": new_cats}})
    print(f"Successfully added {len(new_cats) - len(existing_categories)} new unique categories! Total is now {len(new_cats)}.")
else:
    print("No settings found to update.")
