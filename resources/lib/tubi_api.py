# -*- coding: utf-8 -*-
"""
Tubi TV API Client
Handles all communication with the Tubi TV API
Based on analysis of TubiPlayer Android implementation
"""

import json
import time
import hashlib
import hmac
import base64
import uuid
import requests
from urllib.parse import urlencode, parse_qs, urlparse, quote
import xbmc
from .utils import log, get_setting, set_setting, cache_get, cache_set

class TubiAPI:
    """Main API client for Tubi TV"""
    
    # Base URLs
    BASE_URL = "https://tubitv.com"
    API_URL = "https://tubitv.com/api"
    CDN_URL = "https://tubitv-content.s3.amazonaws.com"
    STATIC_URL = "https://static.tubitv.com"
    
    # API versioning
    API_VERSION = "v1"
    API_URL_V2 = "https://tubitv.com/api/v2"
    
    # Platform identifiers
    PLATFORM = "web"
    APP_VERSION = "3.0.0"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://tubitv.com/',
            'Origin': 'https://tubitv.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
        # Load saved session
        self.auth_token = get_setting('auth_token', '')
        self.user_id = get_setting('user_id', '')
        self.device_id = get_setting('device_id', self._generate_device_id())
        
        # Set up session headers
        self._update_session_headers()
        
        # Region settings
        self.region = get_setting('region', '')
        
        log(f"TubiAPI initialized with device_id: {self.device_id[:8]}...")
    
    def _generate_device_id(self):
        """Generate a unique device ID"""
        device_id = str(uuid.uuid4()).replace('-', '')
        set_setting('device_id', device_id)
        return device_id
    
    def _update_session_headers(self):
        """Update session headers with current authentication"""
        # Device headers
        self.session.headers.update({
            'X-Device-Id': self.device_id,
            'X-Platform': self.PLATFORM,
            'X-App-Version': self.APP_VERSION
        })
        
        # Region header if set
        if self.region:
            self.session.headers['X-Region'] = self.region
        
        # Authentication header if available
        if self.auth_token:
            self.session.headers['Authorization'] = f'Bearer {self.auth_token}'
        elif 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def _request(self, method, endpoint, params=None, data=None, headers=None, api_version='v1'):
        """
        Make an API request with error handling
        Supports both v1 and v2 API endpoints
        """
        # Determine API URL based on version
        if api_version == 'v2':
            base_url = self.API_URL_V2
        else:
            base_url = self.API_URL
        
        url = f"{base_url}{endpoint}"
        
        # Merge headers
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            log(f"API Request: {method} {url}")
            if params:
                log(f"Params: {params}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
                timeout=30
            )
            
            # Log response status
            log(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                return response.json() if response.content else {'success': True}
            elif response.status_code == 204:
                return {'success': True}
            elif response.status_code == 401:
                log("Authentication failed, token may be expired", xbmc.LOGWARNING)
                if self.auth_token:
                    self._refresh_token()
                    return self._request(method, endpoint, params, data, headers)
                return None
            elif response.status_code == 403:
                log("Access forbidden - region block or insufficient permissions", xbmc.LOGWARNING)
                return {'error': 'forbidden', 'message': 'Content not available in your region'}
            elif response.status_code == 404:
                log(f"Endpoint not found: {endpoint}", xbmc.LOGWARNING)
                return None
            elif response.status_code == 429:
                log("Rate limited", xbmc.LOGWARNING)
                # Implement retry with backoff
                time.sleep(1)
                return self._request(method, endpoint, params, data, headers)
            else:
                log(f"API Error {response.status_code}: {response.text[:200]}", xbmc.LOGERROR)
                return None
                
        except requests.exceptions.RequestException as e:
            log(f"Request error: {str(e)}", xbmc.LOGERROR)
            return None
        except json.JSONDecodeError as e:
            log(f"JSON decode error: {str(e)}", xbmc.LOGERROR)
            return None
    
    def _refresh_token(self):
        """Refresh authentication token"""
        # Clear current token
        self.auth_token = ''
        set_setting('auth_token', '')
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        # Attempt to refresh using stored credentials
        # This would typically use a refresh token stored securely
        # For now, we'll just require re-authentication
        return False
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return bool(self.auth_token)
    
    # ============ Content Discovery Endpoints ============
    
    def get_categories(self, content_type='all'):
        """Get available categories"""
        cache_key = f'categories_{content_type}_{self.region}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/categories'
        params = {}
        if content_type != 'all':
            params['type'] = content_type
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            categories = data['data']
            cache_set(cache_key, categories, 3600)  # Cache for 1 hour
            return categories
        
        # Return structured fallback categories
        return self._get_fallback_categories()
    
    def get_home_page(self):
        """Get home page content (featured, trending, etc.)"""
        cache_key = f'home_{self.region}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/home'
        params = {
            'include': 'featured,trending,popular,genres'
        }
        
        data = self._request('GET', endpoint, params=params, api_version='v2')
        
        if data and data.get('data'):
            home_data = data['data']
            cache_set(cache_key, home_data, 300)  # Cache for 5 minutes
            return home_data
        
        return {}
    
    def get_movies(self, category='featured', page=1, limit=20, sort_by=None, filters=None):
        """Get movies by category with advanced filtering"""
        cache_key = f'movies_{category}_{page}_{limit}_{sort_by}_{hash(str(filters))}'
        cache_key = cache_key[:250]  # Limit cache key length
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/movies'
        params = {
            'category': category,
            'page': page,
            'limit': limit,
            'include': 'poster,background,genres,cast,crew'
        }
        
        if sort_by:
            params['sort_by'] = sort_by
        
        if filters:
            params.update(filters)
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            movies = self._parse_movies(data['data'])
            cache_set(cache_key, movies, 300)  # Cache for 5 minutes
            return movies
        
        # Return mock data for development
        return self._get_mock_movies(category, page)
    
    def get_tv_shows(self, category='featured', page=1, limit=20, sort_by=None):
        """Get TV shows by category"""
        cache_key = f'tvshows_{category}_{page}_{limit}_{sort_by}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/tv-shows'
        params = {
            'category': category,
            'page': page,
            'limit': limit,
            'include': 'poster,background,genres,cast,crew'
        }
        
        if sort_by:
            params['sort_by'] = sort_by
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            shows = self._parse_tv_shows(data['data'])
            cache_set(cache_key, shows, 300)  # Cache for 5 minutes
            return shows
        
        # Return mock data for development
        return self._get_mock_tv_shows(category, page)
    
    def get_seasons(self, show_id):
        """Get seasons for a TV show"""
        cache_key = f'seasons_{show_id}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = f'/tv-shows/{show_id}/seasons'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            seasons = data['data']
            cache_set(cache_key, seasons, 3600)
            return seasons
        
        # Return fallback seasons
        return [{'number': 1, 'description': 'Season 1', 'id': '1'}]
    
    def get_episodes(self, show_id, season_number):
        """Get episodes for a specific season"""
        cache_key = f'episodes_{show_id}_{season_number}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = f'/tv-shows/{show_id}/seasons/{season_number}/episodes'
        params = {
            'include': 'poster,background,thumbnails'
        }
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            episodes = self._parse_episodes(data['data'])
            cache_set(cache_key, episodes, 3600)
            return episodes
        
        # Return mock data for development
        return self._get_mock_episodes(show_id, season_number)
    
    def get_content_details(self, content_id, content_type='movie'):
        """Get detailed information about a specific movie or TV show"""
        cache_key = f'details_{content_type}_{content_id}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = f'/{content_type}s/{content_id}'
        params = {
            'include': 'poster,background,genres,cast,crew,related,trailers'
        }
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            details = data['data']
            cache_set(cache_key, details, 3600)
            return details
        
        return None
    
    # ============ Playback Endpoints ============
    
    def get_stream_url(self, video_id):
        """
        Get video stream URL with DRM information
        Enhanced based on TubiPlayer Android analysis
        """
        cache_key = f'stream_{video_id}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = f'/video/{video_id}/playback'
        
        # Enhanced headers for playback request
        headers = {
            'X-Device-Id': self.device_id,
            'X-Platform': self.PLATFORM,
            'X-App-Version': self.APP_VERSION,
            'X-Player': 'tubi-player',
            'X-Player-Version': '1.0.0'
        }
        
        # Add region if set
        if self.region:
            headers['X-Region'] = self.region
        
        data = self._request('GET', endpoint, headers=headers)
        
        if data and data.get('data'):
            stream_data = self._parse_stream_data(data['data'])
            
            # Cache the stream data
            cache_set(cache_key, stream_data, 1800)  # Cache for 30 minutes
            
            # Log DRM information
            if stream_data.get('license_url'):
                log(f"DRM protected stream: {stream_data.get('drm_type')}")
            else:
                log("Non-DRM protected stream")
            
            return stream_data
        
        # Try alternative endpoint
        endpoint = f'/video/{video_id}/stream'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            stream_data = self._parse_stream_data(data['data'])
            cache_set(cache_key, stream_data, 1800)
            return stream_data
        
        # Return mock data for development
        return self._get_mock_stream_data(video_id)
    
    def _parse_stream_data(self, data):
        """Parse stream data from API response"""
        stream_data = {
            'url': data.get('url'),
            'manifest_url': data.get('manifest_url') or data.get('url'),
            'license_url': data.get('license_url'),
            'manifest_type': data.get('manifest_type', 'hls'),
            'drm_type': data.get('drm_type', 'widevine'),
            'format': data.get('format', 'hls'),
            'quality': data.get('quality', 'adaptive'),
            'subtitles': data.get('subtitles', []),
            'audio_tracks': data.get('audio_tracks', []),
            'ad_breaks': data.get('ad_breaks', []),  # From TubiPlayer analysis
            'cue_points': data.get('cue_points', []),  # Ad insertion points
            'license_headers': data.get('license_headers', {}),
            'headers': data.get('headers', {})
        }
        
        # Handle ad information from TubiPlayer
        if 'ads' in data:
            stream_data['ads'] = data['ads']
            if 'cue_points' not in stream_data and 'timing' in data['ads']:
                stream_data['cue_points'] = data['ads']['timing']
        
        return stream_data
    
    def get_license_url(self, video_id, drm_type='widevine'):
        """Get license URL for DRM playback"""
        endpoint = f'/video/{video_id}/license'
        
        headers = {
            'X-Device-Id': self.device_id,
            'X-Platform': self.PLATFORM,
            'X-DRM-Type': drm_type
        }
        
        data = self._request('GET', endpoint, headers=headers)
        
        if data and data.get('data'):
            return {
                'license_url': data['data'].get('url'),
                'headers': data['data'].get('headers', {})
            }
        
        return None
    
    # ============ Search Endpoints ============
    
    def search(self, query, page=1, limit=20, content_type=None):
        """
        Search for content
        Enhanced with type filtering
        """
        endpoint = '/search'
        params = {
            'q': query,
            'page': page,
            'limit': limit
        }
        
        if content_type:
            params['type'] = content_type
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            results = self._parse_search_results(data['data'])
            
            # Add type information
            for result in results:
                if not result.get('type'):
                    result['type'] = self._infer_content_type(result)
            
            return results
        
        return []
    
    def search_suggestions(self, query):
        """Get search suggestions"""
        endpoint = '/search/suggestions'
        params = {'q': query}
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            return data['data']
        
        return []
    
    def _infer_content_type(self, item):
        """Infer content type from metadata"""
        if 'episode_count' in item or item.get('type') == 'series':
            return 'tvshow'
        elif item.get('duration') or item.get('year'):
            return 'movie'
        return 'movie'
    
    # ============ User Account Endpoints ============
    
    def login(self, email, password):
        """Authenticate user"""
        endpoint = '/auth/login'
        data = {
            'email': email,
            'password': password,
            'device_id': self.device_id,
            'platform': self.PLATFORM
        }
        
        response = self._request('POST', endpoint, data=data)
        
        if response and response.get('data'):
            auth_data = response['data']
            self.auth_token = auth_data.get('token') or auth_data.get('access_token')
            self.user_id = auth_data.get('user_id') or auth_data.get('id')
            
            if self.auth_token:
                set_setting('auth_token', self.auth_token)
                set_setting('user_id', self.user_id)
                set_setting('refresh_token', auth_data.get('refresh_token', ''))
                
                self._update_session_headers()
                return True
        
        return False
    
    def logout(self):
        """Logout user"""
        if self.is_authenticated():
            endpoint = '/auth/logout'
            self._request('POST', endpoint)
        
        # Clear stored credentials
        self.auth_token = ''
        self.user_id = ''
        set_setting('auth_token', '')
        set_setting('user_id', '')
        set_setting('refresh_token', '')
        self._update_session_headers()
        return True
    
    def get_user_profile(self):
        """Get user profile information"""
        if not self.is_authenticated():
            return None
        
        endpoint = '/user/profile'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            return data['data']
        
        return None
    
    def get_my_list(self):
        """Get user's saved list"""
        if not self.is_authenticated():
            return []
        
        endpoint = '/user/list'
        params = {'include': 'poster,background'}
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            return self._parse_my_list(data['data'])
        
        return []
    
    def add_to_my_list(self, content_id, content_type='movie'):
        """Add content to user's list"""
        if not self.is_authenticated():
            return False
        
        endpoint = '/user/list'
        data = {
            'content_id': content_id,
            'content_type': content_type
        }
        
        response = self._request('POST', endpoint, data=data)
        return response and response.get('success', False)
    
    def remove_from_my_list(self, content_id):
        """Remove content from user's list"""
        if not self.is_authenticated():
            return False
        
        endpoint = f'/user/list/{content_id}'
        response = self._request('DELETE', endpoint)
        return response and response.get('success', False)
    
    def get_watch_history(self):
        """Get user's watch history"""
        if not self.is_authenticated():
            return []
        
        endpoint = '/user/history'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            return data['data']
        
        return []
    
    def update_watch_progress(self, content_id, progress, content_type='movie'):
        """Update watch progress for a video"""
        if not self.is_authenticated():
            return False
        
        endpoint = '/user/progress'
        data = {
            'content_id': content_id,
            'content_type': content_type,
            'progress': progress  # in seconds
        }
        
        response = self._request('POST', endpoint, data=data)
        return response and response.get('success', False)
    
    # ============ Utility Methods ============
    
    def get_device_id(self):
        """Get the current device ID"""
        return self.device_id
    
    def set_region(self, region):
        """Set region code"""
        self.region = region
        set_setting('region', region)
        self._update_session_headers()
    
    def get_region(self):
        """Get current region"""
        return self.region
    
    def check_region(self):
        """Check if content is available in current region"""
        endpoint = '/region/check'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            return data['data'].get('available', False)
        
        return True
    
    def _get_fallback_categories(self):
        """Return fallback categories if API fails"""
        return [
            {'id': 'featured', 'name': 'Featured', 'type': 'all'},
            {'id': 'trending', 'name': 'Trending', 'type': 'all'},
            {'id': 'popular', 'name': 'Popular', 'type': 'all'},
            {'id': 'new-releases', 'name': 'New Releases', 'type': 'all'},
            {'id': 'action', 'name': 'Action', 'type': 'movies'},
            {'id': 'comedy', 'name': 'Comedy', 'type': 'all'},
            {'id': 'drama', 'name': 'Drama', 'type': 'all'},
            {'id': 'horror', 'name': 'Horror', 'type': 'movies'},
            {'id': 'thriller', 'name': 'Thriller', 'type': 'movies'},
            {'id': 'sci-fi', 'name': 'Sci-Fi', 'type': 'all'},
            {'id': 'documentary', 'name': 'Documentary', 'type': 'all'},
            {'id': 'reality', 'name': 'Reality', 'type': 'tvshows'},
            {'id': 'kids', 'name': 'Kids & Family', 'type': 'all'},
            {'id': 'anime', 'name': 'Anime', 'type': 'all'},
            {'id': 'spanish', 'name': 'Español', 'type': 'all'}
        ]
    
    def _get_mock_stream_data(self, video_id):
        """Return mock stream data for development"""
        return {
            'url': f'https://example.com/playlist/{video_id}.m3u8',
            'manifest_url': f'https://example.com/playlist/{video_id}.m3u8',
            'license_url': 'https://example.com/license/widevine',
            'manifest_type': 'hls',
            'drm_type': 'widevine',
            'format': 'hls',
            'quality': 'adaptive',
            'subtitles': [],
            'audio_tracks': [],
            'ad_breaks': [0, 60000, 900000, 1800000],  # From TubiPlayer analysis
            'cue_points': [0, 60000, 900000, 1800000]
        }
    
    # ============ Parse Methods ============
    
    def _parse_movies(self, data):
        """Parse movie data from API response"""
        movies = []
        for item in data:
            movie = {
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'plot': item.get('plot') or item.get('description', ''),
                'thumbnail': item.get('thumbnail') or item.get('poster', ''),
                'poster': item.get('poster') or item.get('thumbnail', ''),
                'background': item.get('background') or item.get('fanart', ''),
                'fanart': item.get('fanart') or item.get('background', ''),
                'year': item.get('year'),
                'duration': item.get('duration', 0),
                'genres': item.get('genres', []),
                'rating': item.get('rating', 0),
                'content_rating': item.get('content_rating') or item.get('mpaa', ''),
                'mpaa': item.get('mpaa') or item.get('content_rating', ''),
                'cast': item.get('cast', []),
                'crew': item.get('crew', []),
                'trailer': item.get('trailer'),
                'type': 'movie'
            }
            movies.append(movie)
        return movies
    
    def _parse_tv_shows(self, data):
        """Parse TV show data from API response"""
        shows = []
        for item in data:
            show = {
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'plot': item.get('plot') or item.get('description', ''),
                'thumbnail': item.get('thumbnail') or item.get('poster', ''),
                'poster': item.get('poster') or item.get('thumbnail', ''),
                'background': item.get('background') or item.get('fanart', ''),
                'fanart': item.get('fanart') or item.get('background', ''),
                'year': item.get('year'),
                'genres': item.get('genres', []),
                'rating': item.get('rating', 0),
                'cast': item.get('cast', []),
                'crew': item.get('crew', []),
                'episode_count': item.get('episode_count'),
                'season_count': item.get('season_count'),
                'type': 'tvshow'
            }
            shows.append(show)
        return shows
    
    def _parse_episodes(self, data):
        """Parse episode data from API response"""
        episodes = []
        for item in data:
            episode = {
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'plot': item.get('plot') or item.get('description', ''),
                'thumbnail': item.get('thumbnail') or item.get('poster', ''),
                'poster': item.get('poster') or item.get('thumbnail', ''),
                'background': item.get('background') or item.get('fanart', ''),
                'fanart': item.get('fanart') or item.get('background', ''),
                'duration': item.get('duration', 0),
                'episode_number': item.get('episode_number', 0),
                'season_number': item.get('season_number', 1),
                'rating': item.get('rating', 0),
                'aired': item.get('aired'),
                'type': 'episode'
            }
            episodes.append(episode)
        return episodes
    
    def _parse_search_results(self, data):
        """Parse search results from API response"""
        results = []
        for item in data:
            result = {
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'plot': item.get('plot') or item.get('description', ''),
                'thumbnail': item.get('thumbnail') or item.get('poster', ''),
                'poster': item.get('poster') or item.get('thumbnail', ''),
                'background': item.get('background') or item.get('fanart', ''),
                'fanart': item.get('fanart') or item.get('background', ''),
                'year': item.get('year'),
                'type': item.get('type', 'movie'),
                'rating': item.get('rating', 0)
            }
            results.append(result)
        return results
    
    def _parse_my_list(self, data):
        """Parse my list data from API response"""
        items = []
        for item in data:
            list_item = {
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'thumbnail': item.get('thumbnail') or item.get('poster', ''),
                'poster': item.get('poster') or item.get('thumbnail', ''),
                'background': item.get('background') or item.get('fanart', ''),
                'fanart': item.get('fanart') or item.get('background', ''),
                'type': item.get('type', 'movie'),
                'added_at': item.get('added_at'),
                'progress': item.get('progress', 0)
            }
            items.append(list_item)
        return items
    
    # ============ Mock Data Methods ============
    
    def _get_mock_movies(self, category, page):
        """Generate mock movie data for development"""
        movies = []
        genres = ['Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi', 'Thriller', 'Romance']
        for i in range(1, 21):
            genre = genres[i % len(genres)]
            movies.append({
                'id': f'movie_{category}_{i}',
                'title': f'Movie {i} - {genre}',
                'description': f'This is a description for movie {i} in the {category} category. A {genre} film that will keep you entertained.',
                'plot': f'This is a description for movie {i} in the {category} category.',
                'thumbnail': 'https://via.placeholder.com/300x450',
                'poster': 'https://via.placeholder.com/300x450',
                'background': 'https://via.placeholder.com/1920x1080',
                'fanart': 'https://via.placeholder.com/1920x1080',
                'year': 2020 + (i % 5),
                'duration': 90 + (i % 60),
                'genres': [genre],
                'rating': 4 + (i % 1),
                'content_rating': 'PG-13',
                'mpaa': 'PG-13',
                'cast': ['Actor 1', 'Actor 2'],
                'crew': ['Director 1'],
                'type': 'movie'
            })
        return movies
    
    def _get_mock_tv_shows(self, category, page):
        """Generate mock TV show data for development"""
        shows = []
        genres = ['Drama', 'Comedy', 'Sci-Fi', 'Documentary', 'Reality']
        for i in range(1, 21):
            genre = genres[i % len(genres)]
            shows.append({
                'id': f'show_{category}_{i}',
                'title': f'TV Show {i} - {genre}',
                'description': f'This is a description for TV show {i} in the {category} category.',
                'plot': f'This is a description for TV show {i} in the {category} category.',
                'thumbnail': 'https://via.placeholder.com/300x450',
                'poster': 'https://via.placeholder.com/300x450',
                'background': 'https://via.placeholder.com/1920x1080',
                'fanart': 'https://via.placeholder.com/1920x1080',
                'year': 2020 + (i % 4),
                'genres': [genre],
                'rating': 4 + (i % 1),
                'cast': ['Actor 1', 'Actor 2'],
                'crew': ['Creator 1'],
                'episode_count': 10 + (i % 10),
                'season_count': 1 + (i % 3),
                'type': 'tvshow'
            })
        return shows
    
    def _get_mock_episodes(self, show_id, season_number):
        """Generate mock episode data for development"""
        episodes = []
        for i in range(1, 11):
            episodes.append({
                'id': f'episode_{show_id}_{season_number}_{i}',
                'title': f'Episode {i}',
                'description': f'Description for episode {i} of season {season_number}',
                'plot': f'Description for episode {i} of season {season_number}',
                'thumbnail': 'https://via.placeholder.com/300x450',
                'poster': 'https://via.placeholder.com/300x450',
                'background': 'https://via.placeholder.com/1920x1080',
                'fanart': 'https://via.placeholder.com/1920x1080',
                'duration': 45,
                'episode_number': i,
                'season_number': season_number,
                'rating': 4 + (i % 1),
                'aired': f'2024-01-{i:02d}',
                'type': 'episode'
            })
        return episodes
