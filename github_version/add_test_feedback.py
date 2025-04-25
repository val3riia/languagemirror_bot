#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script for adding test feedback data to the Language Mirror Bot.
This is useful for testing admin_feedback functionality and report generation system.
"""

import os
import sys
import random
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sample data for generating feedback
SAMPLE_USERS = [
    {"telegram_id": 123456789, "username": "user1", "first_name": "John", "last_name": "Doe"},
    {"telegram_id": 234567890, "username": "user2", "first_name": "Jane", "last_name": "Smith"},
    {"telegram_id": 345678901, "username": "user3", "first_name": "Alex", "last_name": "Johnson"},
    {"telegram_id": 456789012, "username": "user4", "first_name": "Maria", "last_name": "Garcia"},
    {"telegram_id": 567890123, "username": "user5", "first_name": "Michael", "last_name": "Brown"},
]

SAMPLE_RATINGS = ["helpful", "okay", "not_helpful"]

SAMPLE_COMMENTS = [
    "This bot is amazing! It really helped me improve my English.",
    "I like the way it explains words and phrases.",
    "Could be more interactive, but overall it's good.",
    "I didn't understand some of the explanations.",
    "Very natural conversations, feels like talking to a real person.",
    "The reading suggestions were very helpful.",
    "I wish it could provide more examples.",
    "Great for practicing everyday English.",
    "Sometimes responses were too complex for my level.",
    "I'm definitely going to use it more often.",
    None,  # Some users don't leave comments
]

def generate_timestamp():
    """Generate a random timestamp within the last 7 days"""
    days = random.randint(0, 7)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    
    return datetime.now() - timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds
    )

def add_test_feedback(count=10):
    """Add test feedback data"""
    logger.info(f"Adding {count} test feedback entries")
    
    # Check if database connection is available
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        try:
            # Try using Flask app and database
            from flask import Flask
            from models import db, User, Feedback
            
            # Create minimal Flask app
            app = Flask(__name__)
            app.config["SQLALCHEMY_DATABASE_URI"] = database_url
            app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
            db.init_app(app)
            
            with app.app_context():
                # Add feedback entries
                for _ in range(count):
                    # Select random user data
                    user_data = random.choice(SAMPLE_USERS)
                    
                    # Find or create user
                    user = User.query.filter_by(telegram_id=user_data["telegram_id"]).first()
                    if not user:
                        user = User(
                            telegram_id=user_data["telegram_id"],
                            username=user_data["username"],
                            first_name=user_data["first_name"],
                            last_name=user_data["last_name"]
                        )
                        db.session.add(user)
                        db.session.commit()
                    
                    # Create feedback
                    feedback = Feedback(
                        user_id=user.id,
                        rating=random.choice(SAMPLE_RATINGS),
                        comment=random.choice(SAMPLE_COMMENTS),
                        timestamp=generate_timestamp()
                    )
                    
                    db.session.add(feedback)
                    db.session.commit()
                    
                    logger.info(f"Added feedback from {user.username}: {feedback.rating}")
                
                logger.info(f"Successfully added {count} feedback entries to database")
                return True
                
        except Exception as e:
            logger.error(f"Error adding feedback to database: {e}")
            
    # Fallback to API if database not available
    try:
        import requests
        
        for _ in range(count):
            # Select random user data
            user_data = random.choice(SAMPLE_USERS)
            
            # Create feedback data
            feedback_data = {
                "user_id": user_data["telegram_id"],
                "username": user_data["username"],
                "rating": random.choice(SAMPLE_RATINGS),
                "comment": random.choice(SAMPLE_COMMENTS),
                "timestamp": generate_timestamp().isoformat()
            }
            
            # Send to API
            response = requests.post(
                "http://localhost:5000/api/feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Added feedback via API from {user_data['username']}")
            else:
                logger.warning(f"API returned status {response.status_code} when adding feedback")
        
        logger.info(f"Successfully added {count} feedback entries via API")
        return True
        
    except Exception as e:
        logger.error(f"Error adding feedback via API: {e}")
        return False

def main():
    """Main function of the script"""
    # Get number of feedback entries to add from command line argument
    count = 10  # Default
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            logger.error("Invalid count argument. Using default (10)")
    
    # Add test feedback
    success = add_test_feedback(count)
    
    if success:
        print(f"Successfully added {count} test feedback entries")
    else:
        print("Failed to add test feedback. Check logs for details")

if __name__ == "__main__":
    main()