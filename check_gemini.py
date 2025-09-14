#!/usr/bin/env python3
"""
Check Gemini availability and list models.
"""

import vertexai
from vertexai.generative_models import GenerativeModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
vertexai.init(project="semgrep-472018", location="us-central1")

try:
    # Try to initialize Gemini
    logger.info("Checking Gemini models...")

    # Try gemini-1.5-flash
    model = GenerativeModel("gemini-1.5-flash-001")
    logger.info("✓ gemini-1.5-flash-001 is available")

    # Simple test
    response = model.generate_content("Say 'PDF extraction ready' if you can process PDFs.")
    logger.info(f"Response: {response.text}")

except Exception as e:
    logger.error(f"Gemini not available: {e}")

    # Try alternative model
    try:
        model = GenerativeModel("gemini-1.5-pro-001")
        logger.info("✓ gemini-1.5-pro-001 is available")
    except:
        logger.info("Trying gemini-pro...")
        try:
            model = GenerativeModel("gemini-pro")
            logger.info("✓ gemini-pro is available")
        except Exception as e2:
            logger.error(f"No Gemini models available: {e2}")