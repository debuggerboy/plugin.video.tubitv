# -*- coding: utf-8 -*-
"""
Utility functions for the Tubi TV add-on
"""

import json
import os
import time
import xbmc
import xbmcaddon
import xbmcvfs

# Add-on constants
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))

# Cache settings
CACHE_FILE = os.path.join(ADDON_PROFILE, 'cache.json')
CACHE_TTL = 300  # Default 5 minutes

def log(msg, level=xbmc.LOGINFO):
    """Log a message to the Kodi log file"""
    xbmc.log(f"[Tubi TV] {msg}", level)

def get_setting(key, default=''):
    """Get a setting value"""
    return ADDON.getSetting(key) or default

def set_setting(key, value):
    """Set a setting value"""
    ADDON.setSetting(key, str(value))

def cache_get(key):
    """Get a value from the cache"""
    try:
        if not xbmcvfs.exists(CACHE_FILE):
            return None
        
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        if key in cache:
            entry = cache[key]
            if time.time() - entry['timestamp'] < entry.get('ttl', CACHE_TTL):
                return entry['data']
            else:
                # Remove expired entry
                del cache[key]
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
        
        return None
    except Exception as e:
        log(f"Cache read error: {str(e)}", xbmc.LOGWARNING)
        return None

def cache_set(key, data, ttl=CACHE_TTL):
    """Set a value in the cache"""
    try:
        # Ensure cache directory exists
        if not xbmcvfs.exists(ADDON_PROFILE):
            xbmcvfs.mkdirs(ADDON_PROFILE)
        
        # Read existing cache
        cache = {}
        if xbmcvfs.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        
        # Update cache
        cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl
        }
        
        # Write cache
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
            
    except Exception as e:
        log(f"Cache write error: {str(e)}", xbmc.LOGWARNING)

def clear_cache():
    """Clear the entire cache"""
    try:
        if xbmcvfs.exists(CACHE_FILE):
            xbmcvfs.delete(CACHE_FILE)
        log("Cache cleared successfully")
    except Exception as e:
        log(f"Error clearing cache: {str(e)}", xbmc.LOGERROR)

def format_duration(seconds):
    """Format duration in seconds to human readable format"""
    if not seconds:
        return ""
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def safe_unicode(text):
    """Safe conversion to unicode"""
    if isinstance(text, bytes):
        return text.decode('utf-8')
    return str(text)

def clean_string(text):
    """Clean a string for display"""
    if not text:
        return ""
    return ' '.join(text.split())
