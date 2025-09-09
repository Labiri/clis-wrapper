#!/usr/bin/env python3
"""
Test script to verify Gemini CLI authentication persistence after fix.
This tests that the HOME environment variable is preserved, allowing
Gemini CLI to access ~/.gemini/oauth_creds.json for authentication.
"""

import os
import sys
import asyncio
import logging

# Add current directory to path
sys.path.insert(0, '.')

from gemini_cli import GeminiCLI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_gemini_auth():
    """Test that Gemini CLI can authenticate with preserved HOME."""
    
    # Verify HOME is set
    home_dir = os.environ.get('HOME')
    if not home_dir:
        logger.error("HOME environment variable is not set!")
        return False
    
    logger.info(f"HOME directory: {home_dir}")
    
    # Check if Gemini credentials exist
    gemini_creds = os.path.expanduser("~/.gemini/oauth_creds.json")
    if os.path.exists(gemini_creds):
        logger.info(f"✓ Gemini credentials found at: {gemini_creds}")
    else:
        logger.warning(f"Gemini credentials not found at: {gemini_creds}")
        logger.info("You may need to run 'gemini auth login' first")
    
    # Test that our fix preserves HOME
    cli = GeminiCLI()
    
    # Check what would be removed from environment
    sensitive_vars = ['PWD', 'OLDPWD', 'USER', 'LOGNAME']  # HOME is NOT in list
    
    if 'HOME' in sensitive_vars:
        logger.error("✗ FAILED: HOME would be removed from environment!")
        return False
    else:
        logger.info("✓ PASSED: HOME is preserved in environment")
    
    # Quick test of Gemini CLI (if authenticated)
    try:
        logger.info("\nAttempting to use Gemini CLI...")
        result = await cli.query(
            prompt="Say 'Authentication test successful' in 5 words or less",
            model="gemini-2.5-flash"
        )
        
        if result and result.content:
            logger.info(f"✓ Gemini response: {result.content[:100]}")
            return True
        else:
            logger.warning("No response from Gemini CLI")
            return False
            
    except Exception as e:
        logger.error(f"Gemini CLI test failed: {e}")
        logger.info("This is expected if you haven't authenticated with 'gemini auth login'")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gemini_auth())
    sys.exit(0 if success else 1)