from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId

class AutomationRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
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
            "Catering Services", "Auto Repair"
        ]
        default_locations = [
            "Sunnyvale, CA", "Santa Clara, CA", "Mountain View, CA", "Palo Alto, CA",
            "San Mateo, CA", "Redwood City, CA", "Fremont, CA", "Pleasanton, CA",
            "San Ramon, CA", "Walnut Creek, CA", "Concord, CA", "Bakersfield, CA",
            "Modesto, CA", "Stockton, CA", "Sacramento, CA", "Elk Grove, CA",
            "Rancho Cordova, CA", "Davis, CA", "Woodland, CA", "Napa, CA",
            "San Rafael, CA", "Novato, CA", "Petaluma, CA", "Santa Rosa, CA", "Berkeley, CA"
        ]
        
        if not doc:
            # Insert default settings
            default_settings = {
                "enabled": False,
                "subject_template": "Helping {{company}} Strengthen Its Online Presence",
                "body_template": "Hello {{first_name}},\n\nI hope you're doing well.\n\nWhile researching businesses in the {{industry}} sector across {{location}}, I came across {{company}}. I was impressed by your local presence and the reputation you've built within your community.\n\nI noticed that customers currently rely primarily on {{current_platform}}, as there doesn't appear to be a dedicated business website. While social media and business listings are great for visibility, many customers prefer visiting a professional website before making a purchase, booking a service, or getting in touch.\n\nA dedicated website could help you:\n\n• Showcase your {{service_type}} with a clean, modern design\n• Display your contact information, business hours, and location in one place\n• Improve your visibility on Google through local SEO\n• Promote offers, announcements, and new services more effectively\n• Build greater trust with new customers and strengthen your brand online\n\nAt Progix Technologies LLP, we help businesses create modern, mobile-friendly websites designed to improve customer experience, increase online visibility, and generate more direct enquiries.\n\nIf you're interested, we'd be happy to prepare a complimentary homepage concept tailored specifically for {{company}}, along with a few ideas on how your online presence could be further enhanced.\n\nThank you for your time, and I look forward to hearing from you.\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP\n📞 +1 (916) 702-8905\n✉️ progixtechnology@gmail.com\n🌐 https://www.progixtechnology.com/",
                "search_index": 0,
                "categories": default_categories,
                "locations": default_locations,
                "facebook_only": False,
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
                    "Dentists", "Catering Services", "Auto Repair"
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
        return await self.records_col.count_documents({})

    async def count_records_today(self) -> int:
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.records_col.count_documents({"sent_at": {"$gte": start_of_day}})

    async def create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["sent_at"] = datetime.utcnow()
        result = await self.records_col.insert_one(data)
        created = await self.records_col.find_one({"_id": result.inserted_id})
        return self._format_id(created)
