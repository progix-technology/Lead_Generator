import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# 1. Reusable Keyword Expansion Dictionary
KEYWORD_EXPANSIONS: Dict[str, List[str]] = {
    "restaurant": [
        "restaurant", "italian restaurant", "chinese restaurant", "japanese restaurant",
        "mexican restaurant", "seafood restaurant", "cafe", "coffee shop", "bakery",
        "fast food restaurant", "fine dining restaurant", "sushi restaurant", "steakhouse",
        "bistro", "diner", "pizzeria", "burger joint", "breakfast cafe"
    ],
    "dentist": [
        "dentist", "dental clinic", "dental office", "cosmetic dentist", "orthodontist",
        "emergency dentist", "pediatric dentist", "oral surgeon", "endodontist",
        "periodontist", "teeth whitening", "family dentistry", "dental implants"
    ],
    "plumber": [
        "plumber", "plumbing services", "leak repair", "drain cleaning", "emergency plumber",
        "clogged drain repair", "water heater installation", "sewer line repair",
        "commercial plumbing", "residential plumbing", "pipe repair"
    ],
    "carpenter": [
        "carpenter", "carpentry services", "custom cabinets", "woodworking",
        "furniture repair", "home framing", "deck builder", "trim carpentry"
    ],
    "painter": [
        "house painter", "commercial painter", "painting contractor", "interior painting",
        "exterior painting", "residential painting", "cabinet painting"
    ],
    "roofing": [
        "roofing contractor", "roof repair", "roof replacement", "roofing services",
        "commercial roofing", "residential roofing", "gutter installation"
    ],
    "hvac": [
        "hvac contractor", "air conditioning repair", "heating repair", "hvac services",
        "furnace installation", "commercial hvac", "residential hvac", "ac maintenance"
    ],
    "electrician": [
        "electrician", "electrical contractor", "electrical repair", "electrical installation",
        "commercial electrician", "residential electrician", "emergency electrician"
    ],
    "lawyer": [
        "law firm", "attorney", "corporate lawyer", "family lawyer", "criminal lawyer",
        "personal injury lawyer", "bankruptcy attorney", "estate planning attorney"
    ],
    "accountant": [
        "accountant", "accounting firm", "certified public accountant", "cpa",
        "bookkeeper", "tax preparation", "business accountant", "corporate tax service"
    ],
    "solar": [
        "solar panel installers", "solar energy company", "solar power installation",
        "residential solar", "commercial solar panels"
    ],
    "pool": [
        "swimming pool builders", "pool installation", "pool contractor",
        "custom pool design", "pool renovation"
    ],
    "builder": [
        "custom home builders", "home renovation", "general contractor",
        "custom home design", "building contractor"
    ],
    "interior designer": [
        "interior designer", "interior decorator", "home staging",
        "residential interior design", "commercial interior design"
    ],
    "logistics": [
        "logistics company", "freight forwarder", "trucking company",
        "shipping services", "warehouse logistics", "supply chain solutions"
    ],
    "consultant": [
        "consulting agency", "business consultant", "management consulting",
        "financial consultant", "strategy consulting"
    ],
    "event planner": [
        "event planner", "corporate event planner", "party planner",
        "wedding planner", "conference planner"
    ]
}

# 2. City-Level Expansion for States or Large Locations
STATE_CITIES: Dict[str, List[str]] = {
    "california": [
        "Sunnyvale", "Santa Clara", "Mountain View", "Palo Alto", "San Mateo",
        "Redwood City", "Fremont", "Pleasanton", "San Ramon", "Walnut Creek",
        "Concord", "Bakersfield", "Modesto", "Stockton", "Sacramento",
        "Elk Grove", "Rancho Cordova", "Davis", "Woodland", "Napa",
        "San Rafael", "Novato", "Petaluma", "Santa Rosa", "Berkeley"
    ],
    "ca": [
        "Sunnyvale", "Santa Clara", "Mountain View", "Palo Alto", "San Mateo",
        "Redwood City", "Fremont", "Pleasanton", "San Ramon", "Walnut Creek",
        "Concord", "Bakersfield", "Modesto", "Stockton", "Sacramento",
        "Elk Grove", "Rancho Cordova", "Davis", "Woodland", "Napa",
        "San Rafael", "Novato", "Petaluma", "Santa Rosa", "Berkeley"
    ],
    "germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"],
    "usa": ["Austin", "Seattle", "Boston", "San Jose", "San Francisco", "Denver", "Miami", "Chicago", "Dallas"],
    "us": ["Austin", "Seattle", "Boston", "San Jose", "San Francisco", "Denver", "Miami", "Chicago", "Dallas"],
    "uk": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool"]
}

def expand_keyword(category: str) -> List[str]:
    """Expands a category keyword into a list of specific sub-categories / niches."""
    cat_lower = category.lower().strip()
    
    # Try direct mapping
    for key, val in KEYWORD_EXPANSIONS.items():
        if key in cat_lower or cat_lower in key:
            return val
            
    # Fallback to simple variations if not pre-configured
    return [
        category,
        f"{category} clinic" if "clinic" not in cat_lower else category,
        f"{category} office" if "office" not in cat_lower else category,
        f"{category} services" if "services" not in cat_lower else category,
        f"local {category}",
        f"best {category}"
    ]

def get_city_level_locations(location: str) -> List[str]:
    """If the location is strictly a state or country, expands it to city-level granularity. Keeps city level intact."""
    if not location:
        return [""]
        
    loc_clean = location.strip()
    
    # If the location is already a specific city + state (contains comma, e.g. "San Diego, CA"),
    # do not expand it to other cities.
    if "," in loc_clean:
        return [loc_clean]
        
    loc_lower = loc_clean.lower().replace(" ", "")
    
    # Check if we have city-level granularity pre-configured
    for state, cities in STATE_CITIES.items():
        if state == loc_lower:
            return [f"{city}, {loc_clean}" for city in cities[:8]]  # Target top 8 cities
            
    return [loc_clean]

def generate_search_queries(category: str, location: str) -> List[str]:
    """Generates a list of high-quality search queries/phrases with operators & contact-intent modifiers."""
    base_queries = [
        f'"{category} in {location}"',  # Strict phrase matching
        f'"{category} {location}"',
        f"{category} {location} contact",
        f"{category} {location} phone",
        f"{category} {location} email",
        f"{category} {location} official website",
        f"{category} {location} Google Maps",
        f"{category} {location} business",
        f"best {category} {location}",
        f"local {category} {location}"
    ]
    
    # Apply search exclusions to filter directories
    exclusions = " -reddit -tripadvisor -yelp -wikipedia -directory"
    
    final_queries = []
    for q in base_queries[:5]:  # Take top 5 search query styles to avoid excessive API requests
        final_queries.append(f"{q}{exclusions}")
        
    return final_queries

def generate_map_search_queries(category: str, location: str) -> List[str]:
    """Generates clean, maps-friendly search phrases (without boolean exclusions or contact modifiers)."""
    return [
        f"{category} in {location}",
        f"{category} {location}",
        f"{category} near {location}"
    ]

def normalize_business_name(name: str) -> str:
    """Normalizes business name to prevent duplicates (ignores casing, accents, punctuation & spaces)."""
    if not name:
        return ""
    name_clean = name.lower()
    # Strip common suffixes/types to prevent near-duplicates
    name_clean = re.sub(r'\b(inc|llc|ltd|co|corp|corporation|llp|gmbh|and co|& co|company|group|associates|clinic|office)\b', '', name_clean)
    # Strip all non-alphanumeric characters
    name_clean = re.sub(r'[^a-z0-9]', '', name_clean)
    return name_clean.strip()

def deduplicate_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicates a list of leads by normalizing their name and checking for duplicate URLs or phones."""
    seen_names = set()
    seen_urls = set()
    seen_phones = set()
    unique_leads = []
    
    for lead in leads:
        name = lead.get("name", "")
        norm_name = normalize_business_name(name)
        url = (lead.get("website_url") or "").lower().strip()
        phone = (lead.get("phone_number") or "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Skip if name normalized matches
        if norm_name in seen_names:
            continue
            
        # If they have a website and we've already processed this website, skip
        if url and url != "" and url in seen_urls:
            continue
            
        # If they have a phone and we've already processed this phone, skip
        if phone and phone != "" and phone in seen_phones:
            continue
            
        seen_names.add(norm_name)
        if url:
            seen_urls.add(url)
        if phone:
            seen_phones.add(phone)
            
        unique_leads.append(lead)
        
    return unique_leads
