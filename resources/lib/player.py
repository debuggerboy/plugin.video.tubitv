# -*- coding: utf-8 -*-
"""
Video player for Tubi TV
Handles playback with DRM support
"""

import xbmc
import xbmcgui
import xbmcplugin
from .utils import log

class TubiPlayer:
    """Handles video playback with DRM support"""
    
    def __init__(self):
        self.is_playing = False
    
    def play_video(self, video_id, stream_url, title, thumbnail, description, 
                   season='', episode='', license_url=None, manifest_type='hls'):
        """Play a video with proper DRM setup"""
        log(f"Playing video: {title} (ID: {video_id})")
        
        try:
            # Create list item
            list_item = xbmcgui.ListItem(label=title)
            
            # Set basic properties
            list_item.setPath(stream_url)
            list_item.setContentLookup(False)
            
            # Set artwork
            artwork = {
                'thumb': thumbnail,
                'poster': thumbnail,
                'fanart': thumbnail
            }
            list_item.setArt(artwork)
            
            # Set video info
            info = {
                'title': title,
                'plot': description,
                'mediatype': 'movie' if not season else 'episode'
            }
            
            if season and episode:
                info.update({
                    'season': int(season),
                    'episode': int(episode),
                    'mediatype': 'episode'
                })
            
            list_item.setInfo('video', info)
            
            # Set up inputstream.adaptive for DRM
            if license_url:
                # Setup Widevine DRM
                list_item.setProperty('inputstream', 'inputstream.adaptive')
                list_item.setProperty('inputstream.adaptive.manifest_type', manifest_type)
                list_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                list_item.setProperty('inputstream.adaptive.license_key', license_url)
                list_item.setProperty('inputstream.adaptive.license_flags', 'persistent')
                list_item.setProperty('inputstream.adaptive.stream_headers', self._get_headers())
                
                # Set stream properties
                list_item.setProperty('inputstream.adaptive.chunk_count', '3')
                list_item.setProperty('inputstream.adaptive.chunk_timeout', '20')
                list_item.setProperty('inputstream.adaptive.max_bandwidth', '0')
                
                log(f"DRM playback configured: {manifest_type}")
                
            else:
                # Non-DRM playback
                log("Non-DRM playback")
                list_item.setContentLookup(False)
            
            # Resolve the URL
            player_handle = xbmcplugin.get_plugin_handle()
            xbmcplugin.setResolvedUrl(player_handle, True, list_item)
            
            self.is_playing = True
            
        except Exception as e:
            log(f"Error playing video: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Tubi TV", f"Error playing video: {str(e)}")
    
    def _get_headers(self):
        """Get headers for streaming"""
        headers = (
            "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36,"
            "Accept=application/json, text/plain, */*,"
            "Referer=https://tubitv.com/"
        )
        return headers
    
    def stop(self):
        """Stop current playback"""
        if self.is_playing:
            xbmc.Player().stop()
            self.is_playing = False
