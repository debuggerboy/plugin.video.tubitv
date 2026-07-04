# -*- coding: utf-8 -*-
"""
Video player for Tubi TV
Handles playback with DRM support including Widevine and PlayReady
Based on analysis of TubiPlayer Android implementation
"""

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from .utils import log, get_setting

# Add-on constants
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

class TubiPlayer:
    """Handles video playback with comprehensive DRM support"""
    
    def __init__(self):
        self.is_playing = False
        self.player = None
        self.monitor = xbmc.Monitor()
        
        # DRM settings from addon configuration
        self.drm_enabled = get_setting('drm_enabled', 'true') == 'true'
        self.license_proxy = get_setting('license_proxy', '')
        self.preferred_drm = get_setting('preferred_drm', 'widevine')
    
    def play_video(self, video_id, stream_url, title, thumbnail, description, 
                   season='', episode='', license_url=None, manifest_type='hls',
                   drm_type='widevine', headers=None, ad_cue_points=None,
                   subtitles=None, audio_tracks=None, duration=0):
        """
        Play a video with proper DRM setup
        Enhanced based on TubiPlayer Android implementation
        """
        log(f"Playing video: {title} (ID: {video_id})")
        log(f"Stream URL: {stream_url}")
        log(f"DRM Type: {drm_type}, License URL: {license_url}")
        
        try:
            # Create list item
            list_item = xbmcgui.ListItem(label=title)
            
            # Set basic properties
            list_item.setPath(stream_url)
            list_item.setContentLookup(False)
            list_item.setMimeType('application/vnd.apple.mpegurl')
            
            # Set artwork with fallbacks
            artwork = {
                'thumb': thumbnail or self._get_default_artwork('thumb'),
                'poster': thumbnail or self._get_default_artwork('poster'),
                'fanart': description.get('fanart', '') if isinstance(description, dict) else '',
                'clearart': '',
                'clearlogo': '',
                'landscape': '',
                'banner': ''
            }
            
            # If description is a dict with artwork, extract it
            if isinstance(description, dict):
                if 'fanart' in description:
                    artwork['fanart'] = description['fanart']
                if 'banner' in description:
                    artwork['banner'] = description['banner']
                plot = description.get('plot', '')
            else:
                plot = description
            
            list_item.setArt(artwork)
            
            # Set video info with comprehensive metadata
            info = {
                'title': title,
                'plot': plot,
                'mediatype': 'movie' if not season else 'episode',
                'duration': duration,
                'studio': 'Tubi TV',
                'network': 'Tubi TV',
                'genre': 'Movie' if not season else 'TV Series'
            }
            
            if season and episode:
                info.update({
                    'season': int(season),
                    'episode': int(episode),
                    'mediatype': 'episode',
                    'tvshowtitle': self._extract_show_title(title, season)
                })
            
            list_item.setInfo('video', info)
            
            # Add subtitles if available
            if subtitles:
                if isinstance(subtitles, list):
                    list_item.setSubtitles(subtitles)
                elif isinstance(subtitles, str):
                    list_item.setSubtitles([subtitles])
            
            # Setup DRM if enabled and license URL is provided
            if self.drm_enabled and license_url:
                self._setup_drm_playback(list_item, stream_url, license_url, 
                                        manifest_type, drm_type, headers)
            else:
                # Non-DRM playback
                log("Non-DRM playback or DRM disabled")
                list_item.setContentLookup(False)
            
            # Add stream selection properties for quality
            list_item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
            
            # Set audio and video preferences
            audio_language = get_setting('audio_language', 'en')
            if audio_language:
                list_item.setProperty('inputstream.adaptive.audio_language', audio_language)
            
            # Handle ad cue points if provided
            if ad_cue_points:
                self._setup_ad_handling(list_item, ad_cue_points)
            
            # Resolve the URL
            player_handle = xbmcplugin.get_plugin_handle()
            result = xbmcplugin.setResolvedUrl(player_handle, True, list_item)
            
            if result:
                self.is_playing = True
                log(f"Playback started successfully for: {title}")
            else:
                log("Failed to resolve URL", xbmc.LOGERROR)
                
        except Exception as e:
            log(f"Error playing video: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Tubi TV", f"Error playing video: {str(e)}")
            self.is_playing = False
    
    def _setup_drm_playback(self, list_item, stream_url, license_url, 
                           manifest_type='hls', drm_type='widevine', headers=None):
        """Setup DRM playback with comprehensive configuration"""
        
        log(f"Setting up DRM playback: {drm_type}, {manifest_type}")
        
        # Basic inputstream.adaptive setup
        list_item.setProperty('inputstream', 'inputstream.adaptive')
        list_item.setProperty('inputstream.adaptive.manifest_type', manifest_type)
        
        # DRM type configuration
        if drm_type.lower() == 'widevine':
            list_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
            
            # Widevine specific properties
            if 'dash' in manifest_type.lower():
                list_item.setProperty('inputstream.adaptive.license_manifest', 'dash')
            elif 'hls' in manifest_type.lower():
                list_item.setProperty('inputstream.adaptive.license_manifest', 'hls')
                list_item.setProperty('inputstream.adaptive.license_stream_url', stream_url)
            
            # License URL configuration
            list_item.setProperty('inputstream.adaptive.license_key', license_url)
            
            # Add license headers if provided
            if headers:
                license_headers = self._format_headers(headers)
                if license_headers:
                    list_item.setProperty('inputstream.adaptive.license_headers', license_headers)
            
            # Persistent license for improved performance
            if get_setting('persistent_license', 'true') == 'true':
                list_item.setProperty('inputstream.adaptive.license_flags', 'persistent')
            
            # Set stream headers
            stream_headers = self._get_stream_headers(headers)
            if stream_headers:
                list_item.setProperty('inputstream.adaptive.stream_headers', stream_headers)
            
            # Widevine security level
            security_level = get_setting('security_level', '')
            if security_level:
                list_item.setProperty('inputstream.adaptive.server_security_level', security_level)
                
        elif drm_type.lower() == 'playready':
            list_item.setProperty('inputstream.adaptive.license_type', 'com.playready')
            list_item.setProperty('inputstream.adaptive.license_key', license_url)
            
            if headers:
                license_headers = self._format_headers(headers)
                if license_headers:
                    list_item.setProperty('inputstream.adaptive.license_headers', license_headers)
        
        elif drm_type.lower() == 'clearkey':
            list_item.setProperty('inputstream.adaptive.license_type', 'clearkey')
            list_item.setProperty('inputstream.adaptive.license_key', license_url)
        
        # Stream properties for optimal playback
        stream_properties = self._get_stream_properties()
        for key, value in stream_properties.items():
            list_item.setProperty(key, value)
        
        # Enable advanced features
        list_item.setProperty('inputstream.adaptive.force_secure_decoder', 
                             get_setting('force_secure_decoder', 'false'))
        list_item.setProperty('inputstream.adaptive.supports_secure_stop', 'true')
        
        log(f"DRM configuration complete: {drm_type}")
    
    def _get_stream_headers(self, custom_headers=None):
        """Get headers for streaming with custom headers support"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/x-mpegURL, application/vnd.apple.mpegurl, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://tubitv.com/',
            'Origin': 'https://tubitv.com'
        }
        
        # Add custom headers if provided
        if custom_headers:
            headers.update(custom_headers)
        
        # Format as string for Kodi property
        return ','.join([f'{k}={v}' for k, v in headers.items() if v])
    
    def _format_headers(self, headers):
        """Format headers for license request"""
        if isinstance(headers, dict):
            return ','.join([f'{k}={v}' for k, v in headers.items() if v])
        elif isinstance(headers, str):
            return headers
        return ''
    
    def _get_stream_properties(self):
        """Get optimal stream properties based on settings"""
        properties = {
            'inputstream.adaptive.chunk_count': get_setting('chunk_count', '3'),
            'inputstream.adaptive.chunk_timeout': get_setting('chunk_timeout', '20'),
            'inputstream.adaptive.max_bandwidth': get_setting('max_bandwidth', '0'),
            'inputstream.adaptive.min_bandwidth': get_setting('min_bandwidth', '0'),
            'inputstream.adaptive.stream_selection_type': 'adaptive',
            'inputstream.adaptive.supports_decryption': 'true'
        }
        
        # Quality preferences
        quality = get_setting('video_quality', 'adaptive')
        if quality != 'adaptive':
            properties['inputstream.adaptive.stream_selection_type'] = 'fixed'
            
        # Buffer settings
        buffer_size = get_setting('buffer_size', '4')
        properties['inputstream.adaptive.buffer_size'] = buffer_size
        
        return properties
    
    def _setup_ad_handling(self, list_item, ad_cue_points):
        """Setup ad handling based on TubiPlayer Android implementation"""
        if not ad_cue_points:
            return
        
        log(f"Setting up ad handling with {len(ad_cue_points)} cue points")
        
        # Format cue points for Kodi
        if isinstance(ad_cue_points, list):
            cue_points_str = ','.join([str(point) for point in ad_cue_points])
            list_item.setProperty('inputstream.adaptive.cue_points', cue_points_str)
        
        # Ad handling properties
        list_item.setProperty('inputstream.adaptive.ad_handling', '1')
        list_item.setProperty('inputstream.adaptive.ad_timeout', get_setting('ad_timeout', '30'))
        
        log("Ad handling configured")
    
    def _extract_show_title(self, title, season):
        """Extract show title from episode title"""
        # Try to extract show name from title
        if ' - ' in title:
            return title.split(' - ')[0]
        return title
    
    def _get_default_artwork(self, art_type):
        """Get default artwork based on type"""
        default_art = {
            'thumb': 'DefaultVideo.png',
            'poster': 'DefaultVideo.png',
            'fanart': 'fanart.jpg'
        }
        return default_art.get(art_type, '')
    
    def get_player_state(self):
        """Get current player state"""
        if not self.is_playing:
            return 'stopped'
        
        player = xbmc.Player()
        if player.isPlaying():
            if player.isPaused():
                return 'paused'
            return 'playing'
        return 'stopped'
    
    def get_current_time(self):
        """Get current playback position"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                return player.getTime()
        return 0
    
    def get_total_time(self):
        """Get total playback duration"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                return player.getTotalTime()
        return 0
    
    def seek(self, position):
        """Seek to position in seconds"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                player.seekTime(position)
                return True
        return False
    
    def pause(self):
        """Pause playback"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                player.pause()
                return True
        return False
    
    def resume(self):
        """Resume playback"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying() and player.isPaused():
                player.pause()  # Toggle pause
                return True
        return False
    
    def stop(self):
        """Stop current playback"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                player.stop()
            self.is_playing = False
            log("Playback stopped")
    
    def set_playback_rate(self, rate):
        """Set playback speed"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                player.setPlaybackSpeed(rate)
                return True
        return False
    
    def get_available_audio_tracks(self):
        """Get available audio tracks"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                return player.getAvailableAudioTracks()
        return []
    
    def get_available_subtitles(self):
        """Get available subtitles"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                return player.getAvailableSubtitleTracks()
        return []
    
    def set_audio_track(self, track_index):
        """Set audio track by index"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                player.setAudioTrack(track_index)
                return True
        return False
    
    def set_subtitle_track(self, track_index):
        """Set subtitle track by index"""
        if self.is_playing:
            player = xbmc.Player()
            if player.isPlaying():
                player.setSubtitleTrack(track_index)
                return True
        return False
    
    def is_drm_enabled(self):
        """Check if DRM is enabled"""
        return self.drm_enabled
    
    def toggle_drm(self, enabled=None):
        """Toggle DRM on/off"""
        if enabled is not None:
            self.drm_enabled = enabled
        else:
            self.drm_enabled = not self.drm_enabled
        
        # Save setting
        from .utils import set_setting
        set_setting('drm_enabled', str(self.drm_enabled))
        log(f"DRM {'enabled' if self.drm_enabled else 'disabled'}")
        return self.drm_enabled
    
    def get_drm_info(self):
        """Get DRM information for current playback"""
        info = {
            'drm_enabled': self.drm_enabled,
            'drm_type': self.preferred_drm,
            'license_proxy': self.license_proxy,
            'is_playing': self.is_playing
        }
        return info
    
    def clear_drm_cache(self):
        """Clear DRM cache/decryption data"""
        # This would need implementation for clearing Widevine CDM data
        # Typically handled by system/Kodi
        log("Requested DRM cache clear")
        xbmc.executebuiltin('ClearCache')  # Kodi's built-in cache clear
        
        # Additional DRM cache clearing if needed
        if self.is_playing:
            self.stop()
        
        return True
