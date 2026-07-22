from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    """Create database connection with resilient socket/pool settings for MongoDB Atlas."""
    try:
        logger.info("Connecting to MongoDB...")
        db_instance.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            retryReads=True,
            retryWrites=True
        )
        db_instance.db = db_instance.client[settings.DATABASE_NAME]
        
        # Ping the database to verify connection
        await db_instance.db.command("ping")
        logger.info("Successfully connected to MongoDB!")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """Close database connection."""
    if db_instance.client is not None:
        logger.info("Closing MongoDB connection...")
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    """Dependency injection to get the database instance."""
    return db_instance.db
