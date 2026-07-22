from pymongo import MongoClient

client = MongoClient("mongodb+srv://progixtechnology_db_user:mmEgsNkhpORYA345@cluster0.hqkvaho.mongodb.net/?appName=Cluster0")
db = client["leadgen_pro"]
collection = db["automation_settings"]

locations = [
    # Nepal
    "Kathmandu, Nepal",
    "Lalitpur, Nepal",
    "Bhaktapur, Nepal",
    "Pokhara, Nepal",
    "Biratnagar, Nepal",
    "Birgunj, Nepal",
    "Butwal, Nepal",
    "Dharan, Nepal",
    "Hetauda, Nepal",
    "Nepalgunj, Nepal",
    "Janakpur, Nepal",
    "Itahari, Nepal",
    "Dhangadhi, Nepal",
    "Tulsipur, Nepal",
    "Ghorahi, Nepal",
    
    # Sri Lanka
    "Colombo, Sri Lanka",
    "Dehiwala, Sri Lanka",
    "Mount Lavinia, Sri Lanka",
    "Kandy, Sri Lanka",
    "Galle, Sri Lanka",
    "Negombo, Sri Lanka",
    "Kurunegala, Sri Lanka",
    "Jaffna, Sri Lanka",
    "Matara, Sri Lanka",
    "Batticaloa, Sri Lanka",
    "Anuradhapura, Sri Lanka",
    "Ratnapura, Sri Lanka",
    "Badulla, Sri Lanka",
    "Kalutara, Sri Lanka",
    "Moratuwa, Sri Lanka"
]

settings = collection.find_one({})
if settings:
    existing_locations = settings.get("locations", [])
    new_locs = existing_locations.copy()
    for loc in locations:
        if loc not in new_locs:
            new_locs.append(loc)
    
    collection.update_one({"_id": settings["_id"]}, {"$set": {"locations": new_locs}})
    print(f"Successfully added {len(new_locs) - len(existing_locations)} new unique locations! Total is now {len(new_locs)}.")
else:
    print("No settings found to update.")
