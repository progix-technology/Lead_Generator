from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId

class AutomationRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self.settings_col = db["automation_settings"]
        self.records_col = db["automation_records"]

    def _format_id(self, doc: dict) -> dict:
        if doc:
            if "_id" in doc:
                doc["id"] = str(doc.pop("_id"))
            for key, val in list(doc.items()):
                if isinstance(val, datetime):
                    if val.tzinfo is None:
                        doc[key] = val.isoformat() + "Z"
                    else:
                        doc[key] = val.isoformat()
        return doc

    async def get_settings(self) -> Dict[str, Any]:
        doc = await self.settings_col.find_one({})
        default_categories = [
            "Carpenters", "Locksmiths", "Paving Contractors", "Painting Contractors",
            "Window Cleaning", "Carpet Cleaning", "House Cleaning", "Tree Services",
            "Drywall Contractors", "Concrete Contractors", "Fence Contractors", "Moving Companies",
            "Towing Services", "Appliance Repair", "Junk Removal", "Physiotherapists",
            "Chiropractors", "Veterinarians", "Acupuncture Clinics", "Optometrists",
            "Yoga Studios", "Dance Schools", "Daycare Centers", "Driving Schools", "Tailor Shops",
            "Roofing Contractors", "HVAC Services", "Plumbers", "Electricians", "Dentists",
            "Catering Services", "Auto Repair",
            "Cosmetic Dentists", "Orthodontists", "IVF Clinics", "Medical Spas", "Corporate Lawyers", "Accountants",
            "Solar Panel Installers", "Swimming Pool Builders", "Custom Home Builders", "Commercial HVAC", "Commercial Roofing", "Interior Designers",
            "Logistics Companies", "Consulting Agencies", "Corporate Event Planners",
            "General Contractors", "Kitchen Remodeling", "Bathroom Remodeling", "Flooring Contractors",
            "Garage Door Repair", "Pest Control", "Water Damage Restoration", "Mold Remediation",
            "Landscaping Services", "Lawn Care", "Pressure Washing", "Gutter Cleaning",
            "Pool Cleaning Services", "Handyman Services", "Deck Builders", "Masonry Contractors",
            "Glass Repair Services", "Emergency Plumbers", "Emergency Electricians", "Septic Services",
            "Mobile Car Detailing", "Tire Shops", "Auto Body Shops", "Windshield Repair",
            "Transmission Repair", "Brake Repair", "Oil Change Services", "Car Wash",
            "Personal Injury Lawyers", "Immigration Lawyers", "Family Lawyers", "Bankruptcy Lawyers",
            "Tax Consultants", "Bookkeeping Services", "Payroll Services", "Insurance Agencies",
            "Real Estate Agents", "Mortgage Brokers", "Property Management", "Home Inspectors",
            "Dermatology Clinics", "Pediatric Clinics", "Dental Implants Clinics", "Urgent Care Clinics",
            "Psychology Clinics", "Speech Therapy Centers", "Occupational Therapy Centers", "Home Healthcare Services",
            "Med Spa Clinics", "Hair Salons", "Nail Salons", "Barber Shops",
            "Beauty Clinics", "Eyelash Studios", "Tattoo Studios", "Massage Therapy",
            "Gyms", "Personal Trainers", "Pilates Studios", "Crossfit Gyms",
            "Martial Arts Schools", "Music Schools", "Tutoring Centers", "Test Prep Centers","Dance Acadmy","Driving Schools"
            "Preschools", "Private Schools", "Senior Care Services", "Assisted Living Facilities",
            "Restaurants", "Coffee Shops", "Bakeries", "Food Trucks", "Italian Restaurants", "Chinese Restaurants", "Japanese Restaurants", "Mexican Restaurants", "Thai Restaurants", "Indian Restaurants","Arebian Restaurants","Asian Restaurants","Seafood Restaurants","Korean Restaurants","Turkish Restaurants",
            "Cafes", "Cloud Kitchens", "Pet Grooming", "Pet Boarding",
            "Recruitment Agencies", "Staffing Agencies", "Printing Services", "Signage Companies", "Security Camera Installation",
            "Dry Cleaners", "Laundromats", "Shoe Repair", "Watch Repair", "Jewelry Stores", "Florists", "Gift Shops", 
            "Boutiques", "Bridal Shops", "Event Planners", "Wedding Planners", "Party Rental", "Photo Booth Rental", 
            "Photographers", "Videographers", "Personal Chefs", "Nutritionists", "Dietitians", "Weight Loss Clinics", 
            "Sleep Clinics", "Fertility Clinics", "Plastic Surgeons", "Podiatrists", "Orthopedic Clinics", "Opticians", 
            "Hearing Aid Clinics", "Pharmacy", "Medical Supply Stores", "Home Security", "Fire Protection Services", 
            "Water Filtration", "Well Drilling", "Asphalt Paving", "Excavating Contractors", "Demolition Contractors", 
            "Scaffolding Rental", "Crane Service", "Dumpster Rental", "Waste Management", "Recycling Centers", 
            "Scrap Metal", "Auto Salvage", "RV Repair", "Boat Repair", "Motorcycle Repair", "Bicycle Repair", 
            "Car Audio Installation", "Window Tinting", "Upholstery Shop", "Furniture Repair", "Cabinet Makers", 
            "Granite Countertops", "Tile Contractors", "Insulation Contractors", "Waterproofing", "Foundation Repair", 
            "Chimney Sweep", "Appliance Stores", "Mattress Stores", "Furniture Stores", "Antique Stores", "Pawn Shops", 
            "Sporting Goods", "Art Galleries", "Custom Framing", "Travel Agencies", "Self Storage", "Moving Supplies", 
            "Notary Public", "Private Investigators", "Security Guards", "Janitorial Services", "Office Cleaning", 
            "Commercial Cleaning", "Carpet Installation", "Hardwood Flooring", "Blinds and Shades", "Awnings", 
            "Tool Rental", "Equipment Rental", "Architects", "Surveyors", "Structural Engineers"
        ]
        default_locations = [
            "Sunnyvale, CA", "Santa Clara, CA", "Mountain View, CA", "Palo Alto, CA",
            "San Mateo, CA", "Redwood City, CA", "Fremont, CA", "Pleasanton, CA",
            "San Ramon, CA", "Walnut Creek, CA", "Concord, CA", "Bakersfield, CA",
            "Modesto, CA", "Stockton, CA", "Sacramento, CA", "Elk Grove, CA",
            "Rancho Cordova, CA", "Davis, CA", "Woodland, CA", "Napa, CA",
            "San Rafael, CA", "Novato, CA", "Petaluma, CA", "Santa Rosa, CA", "Berkeley, CA",
            "Los Angeles, CA", "San Diego, CA", "San Jose, CA", "San Francisco, CA",
            "Long Beach, CA", "Anaheim, CA", "Irvine, CA", "Riverside, CA",
            "Phoenix, AZ", "Mesa, AZ", "Scottsdale, AZ", "Tempe, AZ",
            "Las Vegas, NV", "Henderson, NV", "Reno, NV", "Portland, OR",
            "Seattle, WA", "Tacoma, WA", "Spokane, WA", "Denver, CO",
            "Colorado Springs, CO", "Dallas, TX", "Houston, TX", "Austin, TX",
            "San Antonio, TX", "Fort Worth, TX", "El Paso, TX", "Chicago, IL",
            "Naperville, IL", "Miami, FL", "Orlando, FL", "Tampa, FL",
            "Jacksonville, FL", "Fort Lauderdale, FL", "Atlanta, GA", "Charlotte, NC",
            "Raleigh, NC", "Nashville, TN", "New York, NY", "Brooklyn, NY",
            "Queens, NY", "Buffalo, NY", "Jersey City, NJ", "Newark, NJ",
            "Philadelphia, PA", "Pittsburgh, PA", "Boston, MA", "Worcester, MA",
            "Washington, DC", "Baltimore, MD", "Detroit, MI", "Minneapolis, MN",
            "St. Paul, MN", "Columbus, OH", "Cleveland, OH", "Cincinnati, OH",
            "Indianapolis, IN", "Kansas City, MO", "St. Louis, MO", "New Orleans, LA"
        ]
        
        default_redesign_subject = "Quick suggestion for {{company}} about your website"
        default_redesign_body = "Hello {{first_name}},\n\nI hope you're doing well.\n\nWhile researching businesses in the {{industry}} sector across {{location}}, I checked your website ({{website}}) and ran a quick performance/SEO diagnostic. I noticed a few technical issues that might be affecting your user experience and search ranking:\n\n• Speed/Performance Score: {{performance_score}}/100\n• Mobile/UI Score: {{ui_score}}/100\n• SEO Health Score: {{seo_score}}/100\n\nHere are the specific recommendations generated:\n{{suggestions}}\n\nAt Progix Technologies LLP, we specialize in high-performance web design and SEO. We can rebuild your website to load in under 1.5 seconds, make it 100% mobile-responsive, and integrate direct online bookings to convert more visitors into clients.\n\nWould you be open to a quick call or a 1-page free homepage design mockup next week to see how your site can be modernized?\n\nThank you for your time, and I look forward to hearing from you.\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/"
        
        if not doc:
            # Insert default settings
            default_settings = {
                "enabled": False,
                "subject_template": "Helping {{company}} Strengthen Its Online Presence",
                "body_template": "Hello {{first_name}},\n\nI hope you're doing well.\n\nWhile researching businesses in the {{industry}} sector across {{location}}, I came across {{company}}. I was impressed by your local presence and the reputation you've built within your community.\n\nI noticed that customers currently rely primarily on {{current_platform}}, as there doesn't appear to be a dedicated business website. While social media and business listings are great for visibility, many customers prefer visiting a professional website before making a purchase, booking a service, or getting in touch.\n\nA dedicated website could help you:\n\n• Showcase your {{service_type}} with a clean, modern design\n• Display your contact information, business hours, and location in one place\n• Improve your visibility on Google through local SEO\n• Promote offers, announcements, and new services more effectively\n• Build greater trust with new customers and strengthen your brand online\n\nAt Progix Technologies LLP, we help businesses create modern, mobile-friendly websites designed to improve customer experience, increase online visibility, and generate more direct enquiries.\n\nIf you're interested, we'd be happy to prepare a complimentary homepage concept tailored specifically for {{company}}, along with a few ideas on how your online presence could be further enhanced.\n\nThank you for your time, and I look forward to hearing from you.\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/",
                "redesign_subject_template": default_redesign_subject,
                "redesign_body_template": default_redesign_body,
                "search_index": 0,
                "categories": default_categories,
                "locations": default_locations,
                "facebook_only": False,
                "enable_redesign": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await self.settings_col.insert_one(default_settings)
            doc = await self.settings_col.find_one({"_id": result.inserted_id})
        else:
            # Seed fields if missing from existing document, or reset if they have old values
            needs_update = False
            update_data = {}
            if "categories" not in doc:
                doc["categories"] = default_categories
                update_data["categories"] = default_categories
                needs_update = True
            else:
                current_cats = doc.get("categories", [])
                new_additions = [
                    "Roofing Contractors", "HVAC Services", "Plumbers", "Electricians", 
                    "Dentists", "Catering Services", "Auto Repair",
                    "Cosmetic Dentists", "Orthodontists", "IVF Clinics", "Medical Spas", "Corporate Lawyers", "Accountants",
                    "Solar Panel Installers", "Swimming Pool Builders", "Custom Home Builders", "Commercial HVAC", "Commercial Roofing", "Interior Designers",
                    "Logistics Companies", "Consulting Agencies", "Corporate Event Planners",
                    "General Contractors", "Kitchen Remodeling", "Bathroom Remodeling", "Flooring Contractors",
                    "Garage Door Repair", "Pest Control", "Water Damage Restoration", "Mold Remediation",
                    "Landscaping Services", "Lawn Care", "Pressure Washing", "Gutter Cleaning",
                    "Pool Cleaning Services", "Handyman Services", "Deck Builders", "Masonry Contractors",
                    "Glass Repair Services", "Emergency Plumbers", "Emergency Electricians", "Septic Services",
                    "Mobile Car Detailing", "Tire Shops", "Auto Body Shops", "Windshield Repair",
                    "Transmission Repair", "Brake Repair", "Oil Change Services", "Car Wash",
                    "Personal Injury Lawyers", "Immigration Lawyers", "Family Lawyers", "Bankruptcy Lawyers",
                    "Tax Consultants", "Bookkeeping Services", "Payroll Services", "Insurance Agencies",
                    "Real Estate Agents", "Mortgage Brokers", "Property Management", "Home Inspectors",
                    "Dermatology Clinics", "Pediatric Clinics", "Dental Implants Clinics", "Urgent Care Clinics",
                    "Psychology Clinics", "Speech Therapy Centers", "Occupational Therapy Centers", "Home Healthcare Services",
                    "Med Spa Clinics", "Hair Salons", "Nail Salons", "Barber Shops",
                    "Beauty Clinics", "Eyelash Studios", "Tattoo Studios", "Massage Therapy",
                    "Gyms", "Personal Trainers", "Pilates Studios", "Crossfit Gyms",
                    "Martial Arts Schools", "Music Schools", "Tutoring Centers", "Test Prep Centers",
                    "Preschools", "Private Schools", "Senior Care Services", "Assisted Living Facilities",
                    "Restaurants", "Coffee Shops", "Bakeries", "Food Trucks",
                    "Cafes", "Cloud Kitchens", "Pet Grooming", "Pet Boarding",
                    "Dairy", "Milk", "Farm", "Food","Beverages",
                    "IT Support Services", "Managed IT Services", "Cybersecurity Consultants", "Digital Marketing Agencies",
                    "SEO Agencies", "Web Design Agencies", "Software Development Companies", "Recruitment Agencies",
                    "Staffing Agencies", "Printing Services", "Signage Companies", "Security Camera Installation"
                ]
                merged_needed = False
                for a in new_additions:
                    if a not in current_cats:
                        current_cats.append(a)
                        merged_needed = True
                if merged_needed:
                    doc["categories"] = current_cats
                    update_data["categories"] = current_cats
                    needs_update = True
            if "locations" not in doc or "Kingsburg, CA" in doc.get("locations", []) or "Passaic, NJ" in doc.get("locations", []):
                doc["locations"] = default_locations
                update_data["locations"] = default_locations
                needs_update = True
            else:
                current_locations = doc.get("locations", [])
                new_location_additions = [
                    "Los Angeles, CA", "San Diego, CA", "San Jose, CA", "San Francisco, CA",
                    "Long Beach, CA", "Anaheim, CA", "Irvine, CA", "Riverside, CA",
                    "Phoenix, AZ", "Mesa, AZ", "Scottsdale, AZ", "Tempe, AZ",
                    "Las Vegas, NV", "Henderson, NV", "Reno, NV", "Portland, OR",
                    "Seattle, WA", "Tacoma, WA", "Spokane, WA", "Denver, CO",
                    "Colorado Springs, CO", "Dallas, TX", "Houston, TX", "Austin, TX",
                    "San Antonio, TX", "Fort Worth, TX", "El Paso, TX", "Chicago, IL",
                    "Naperville, IL", "Miami, FL", "Orlando, FL", "Tampa, FL",
                    "Jacksonville, FL", "Fort Lauderdale, FL", "Atlanta, GA", "Charlotte, NC",
                    "Raleigh, NC", "Nashville, TN", "New York, NY", "Brooklyn, NY",
                    "Queens, NY", "Buffalo, NY", "Jersey City, NJ", "Newark, NJ",
                    "Philadelphia, PA", "Pittsburgh, PA", "Boston, MA", "Worcester, MA",
                    "Washington, DC", "Baltimore, MD", "Detroit, MI", "Minneapolis, MN",
                    "St. Paul, MN", "Columbus, OH", "Cleveland, OH", "Cincinnati, OH",
                    "Indianapolis, IN", "Kansas City, MO", "St. Louis, MO", "New Orleans, LA"
                ]
                location_merged = False
                for loc in new_location_additions:
                    if loc not in current_locations:
                        current_locations.append(loc)
                        location_merged = True
                if location_merged:
                    doc["locations"] = current_locations
                    update_data["locations"] = current_locations
                    needs_update = True
            if "facebook_only" not in doc:
                doc["facebook_only"] = False
                update_data["facebook_only"] = False
                needs_update = True
            if "daily_email_limit" not in doc:
                doc["daily_email_limit"] = 20
                update_data["daily_email_limit"] = 20
                needs_update = True
            if "batch_email_limit" not in doc:
                doc["batch_email_limit"] = 5
                update_data["batch_email_limit"] = 5
                needs_update = True
            if "smtp_host" not in doc:
                doc["smtp_host"] = "smtp.gmail.com"
                update_data["smtp_host"] = "smtp.gmail.com"
                needs_update = True
            if "smtp_port" not in doc:
                doc["smtp_port"] = 587
                update_data["smtp_port"] = 587
                needs_update = True
            if "smtp_email" not in doc:
                doc["smtp_email"] = ""
                update_data["smtp_email"] = ""
                needs_update = True
            if "smtp_password" not in doc:
                doc["smtp_password"] = ""
                update_data["smtp_password"] = ""
                needs_update = True
            if "openrouter_api_key" not in doc:
                doc["openrouter_api_key"] = ""
                update_data["openrouter_api_key"] = ""
                needs_update = True
            if "email_service_provider" not in doc:
                doc["email_service_provider"] = "SMTP"
                update_data["email_service_provider"] = "SMTP"
                needs_update = True
            if "resend_api_key" not in doc:
                doc["resend_api_key"] = ""
                update_data["resend_api_key"] = ""
                needs_update = True
            if "sendgrid_api_key" not in doc:
                doc["sendgrid_api_key"] = ""
                update_data["sendgrid_api_key"] = ""
                needs_update = True
            if "sendgrid_sender" not in doc:
                doc["sendgrid_sender"] = ""
                update_data["sendgrid_sender"] = ""
                needs_update = True
            if "enable_redesign" not in doc:
                doc["enable_redesign"] = True
                update_data["enable_redesign"] = True
                needs_update = True
            default_subject = "Helping {{company}} Strengthen Its Online Presence"
            default_body = "Hello {{first_name}},\n\nI hope you're doing well.\n\nWhile researching businesses in the {{industry}} sector across {{location}}, I came across {{company}}. I was impressed by your local presence and the reputation you've built within your community.\n\nI noticed that customers currently rely primarily on {{current_platform}}, as there doesn't appear to be a dedicated business website. While social media and business listings are great for visibility, many customers prefer visiting a professional website before making a purchase, booking a service, or getting in touch.\n\nA dedicated website could help you:\n\n• Showcase your {{service_type}} with a clean, modern design\n• Display your contact information, business hours, and location in one place\n• Improve your visibility on Google through local SEO\n• Promote offers, announcements, and new services more effectively\n• Build greater trust with new customers and strengthen your brand online\n\nAt Progix Technologies LLP, we help businesses create modern, mobile-friendly websites designed to improve customer experience, increase online visibility, and generate more direct enquiries.\n\nIf you're interested, we'd be happy to prepare a complimentary homepage concept tailored specifically for {{company}}, along with a few ideas on how your online presence could be further enhanced.\n\nThank you for your time, and I look forward to hearing from you.\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/"

            default_country_templates = {
                "USA": {
                    "subject_template": default_subject,
                    "body_template": default_body,
                    "redesign_subject_template": default_redesign_subject,
                    "redesign_body_template": default_redesign_body
                },
                "UK": {
                    "subject_template": "Quick enquiry regarding {{company}}'s digital presence in {{location}}",
                    "body_template": "Hello {{first_name}},\n\nI hope this email finds you well.\n\nWhile reviewing local businesses in the {{industry}} sector across {{location}}, I came across {{company}}. I was genuinely impressed by your strong local reputation.\n\nI noticed that customers currently engage with you via {{current_platform}}, as there doesn't appear to be a dedicated corporate website. A bespoke website would assist in showcasing your services and building greater trust with potential clients.\n\nAt Progix Technologies LLP, we craft high-performance, responsive websites designed to convert visitors into clients.\n\nIf you would be open to it, we would be delighted to provide a complimentary homepage concept tailored for {{company}}.\n\nThank you for your time.\n\nWarm regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/",
                    "redesign_subject_template": "Website performance report & recommendations for {{company}}",
                    "redesign_body_template": "Hello {{first_name}},\n\nI hope you are having a pleasant week.\n\nWhile conducting digital audits for {{industry}} firms in {{location}}, I analyzed your website ({{website}}). I observed a few technical areas that may be impacting your visitor conversion rate:\n\n• Speed & Loading Score: {{performance_score}}/100\n• Mobile Usability Score: {{ui_score}}/100\n• Search Health Score: {{seo_score}}/100\n\nSpecific observations:\n{{suggestions}}\n\nWe specialize in building modern, ultra-fast websites engineered to load in under 1.5 seconds and maximize enquiries.\n\nWould you be open to reviewing a complimentary 1-page design concept for {{company}} next week?\n\nKind regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/"
                },
                "UAE": {
                    "subject_template": "Complimentary Digital Growth Audit & Web Proposal for {{company}}",
                    "body_template": "Hello {{first_name}},\n\nGood day to you.\n\nOur team at Progix Technologies LLP is currently evaluating premier B2B and service enterprises in {{location}}. We reviewed {{company}} and admired your established brand presence.\n\nWe noticed that your business currently operates primarily through {{current_platform}} without a dedicated enterprise website. In the UAE market, a premium custom web platform is vital to establish executive trust and capture high-ticket client enquiries.\n\nWe would be honored to create a complimentary custom homepage mockup tailored exclusively for {{company}}.\n\nThank you for your consideration.\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/",
                    "redesign_subject_template": "Executive Web Audit & Modernization Proposal for {{company}}",
                    "redesign_body_template": "Hello {{first_name}},\n\nGood day.\n\nWhile performing technical web diagnostics for leading {{industry}} businesses in {{location}}, we analyzed your portal ({{website}}). Our diagnostic suite identified key performance bottlenecks that may be affecting your executive presentation:\n\n• Performance Index: {{performance_score}}/100\n• Mobile Interface Score: {{ui_score}}/100\n• SEO Authority Score: {{seo_score}}/100\n\nKey Diagnostic Points:\n{{suggestions}}\n\nAt Progix Technologies LLP, we engineer ultra-fast, premium web experiences tailored to elevate corporate authority and boost direct bookings.\n\nWould you be available for a brief call or to view a complimentary redesign mockup for {{company}}?\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/"
                }
            }

            default_country_schedules = {
                "UAE": {
                    "country_name": "Dubai (UAE)",
                    "start_time_ist": "10:00",
                    "end_time_ist": "14:00",
                    "locations": ["Dubai, UAE", "Abu Dhabi, UAE", "Sharjah, UAE", "Ajman, UAE", "Ras Al Khaimah, UAE"]
                },
                "UK": {
                    "country_name": "United Kingdom",
                    "start_time_ist": "15:00",
                    "end_time_ist": "21:00",
                    "locations": ["London, UK", "Manchester, UK", "Birmingham, UK", "Leeds, UK", "Glasgow, UK", "Liverpool, UK", "Edinburgh, UK", "Bristol, UK"]
                },
                "USA": {
                    "country_name": "United States",
                    "start_time_ist": "01:00",
                    "end_time_ist": "04:00",
                    "locations": ["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ", "Dallas, TX", "Miami, FL"]
                }
            }
            
            if not doc.get("country_templates"):
                doc["country_templates"] = default_country_templates
                update_data["country_templates"] = default_country_templates
                needs_update = True
            if not doc.get("country_schedules"):
                doc["country_schedules"] = default_country_schedules
                update_data["country_schedules"] = default_country_schedules
                needs_update = True

            if not doc.get("subject_template"):
                doc["subject_template"] = default_subject
                update_data["subject_template"] = default_subject
                needs_update = True
            if not doc.get("body_template"):
                doc["body_template"] = default_body
                update_data["body_template"] = default_body
                needs_update = True
            if not doc.get("redesign_subject_template"):
                doc["redesign_subject_template"] = default_redesign_subject
                update_data["redesign_subject_template"] = default_redesign_subject
                needs_update = True
            if not doc.get("redesign_body_template"):
                doc["redesign_body_template"] = default_redesign_body
                update_data["redesign_body_template"] = default_redesign_body
                needs_update = True
            if needs_update:
                await self.settings_col.update_one({"_id": doc["_id"]}, {"$set": update_data})
        return self._format_id(doc)

    async def update_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        current = await self.get_settings()
        update_data = {k: v for k, v in data.items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        await self.settings_col.update_one(
            {"_id": ObjectId(current["id"])},
            {"$set": update_data}
        )
        updated = await self.settings_col.find_one({"_id": ObjectId(current["id"])})
        return self._format_id(updated)

    async def get_records(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.records_col.find({}).sort("sent_at", -1).skip(skip).limit(limit)
        return [self._format_id(doc) async for doc in cursor]

    async def count_records(self) -> int:
        return await self.records_col.count_documents({"status": "Sent"})

    async def count_records_today(self) -> int:
        from datetime import datetime, timezone
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.records_col.count_documents({
            "sent_at": {"$gte": start_of_day},
            "status": "Sent"
        })

    async def create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["created_at"] = datetime.utcnow()
        if data.get("status") == "Sent":
            data["sent_at"] = datetime.utcnow()
        result = await self.records_col.insert_one(data)
        created = await self.records_col.find_one({"_id": result.inserted_id})
        return self._format_id(created)

    async def get_pending_emails(self, limit: int = 10, exclude_redesign: bool = False) -> List[Dict[str, Any]]:
        query = {"status": "Pending_Email"}
        if exclude_redesign:
            query["metadata.is_redesign"] = {"$ne": True}
        
        # Prioritize standard emails (no website) over redesign emails
        # Sorting by metadata.is_redesign asc puts missing/False values first, and True values last.
        cursor = self.records_col.find(query).sort([
            ("metadata.is_redesign", 1),
            ("created_at", 1)
        ]).limit(limit)
        return [self._format_id(doc) async for doc in cursor]

    async def count_pending_records(self) -> int:
        return await self.records_col.count_documents({"status": "Pending_Email"})
        
    async def count_pending_redesign_records(self) -> int:
        return await self.records_col.count_documents({"status": "Pending_Email", "metadata.is_redesign": True})
        
    async def count_pending_standard_records(self) -> int:
        return await self.records_col.count_documents({"status": "Pending_Email", "metadata.is_redesign": {"$ne": True}})
        
    async def update_record_status(self, record_id: str, status: str, error_message: str = None) -> None:
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if error_message is not None:
            update_data["error_message"] = error_message
        if status == "Sent":
            update_data["sent_at"] = datetime.utcnow()
            
        await self.records_col.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_data}
        )
