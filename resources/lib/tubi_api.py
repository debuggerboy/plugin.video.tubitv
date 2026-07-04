# -*- coding: utf-8 -*-
"""
Tubi TV API Client
Handles all communication with the Tubi TV API
"""

import json
import time
import hashlib
import requests
from urllib.parse import urlencode, parse_qs, urlparse
import xbmc
from .utils import log, get_setting, set_setting, cache_get, cache_set

class TubiAPI:
    """Main API client for Tubi TV"""
    
    BASE_URL = "https://tubitv.com"
    API_URL = "https://tubitv.com/api"
    CDN_URL = "https://tubitv-content.s3.amazonaws.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://tubitv.com/',
            'Origin': 'https://tubitv.com',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        
        # Load saved session
        self.auth_token = get_setting('auth_token', '')
        self.user_id = get_setting('user_id', '')
        
        if self.auth_token:
            self.session.headers['Authorization'] = f'Bearer {self.auth_token}'
    
    def _request(self, method, endpoint, params=None, data=None, headers=None):
        """Make an API request with error handling"""
        url = f"{self.API_URL}{endpoint}"
        
        if headers:
            self.session.headers.update(headers)
        
        try:
            log(f"API Request: {method} {url}")
            if params:
                log(f"Params: {params}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                log("Authentication failed, token may be expired", xbmc.LOGWARNING)
                # Try to refresh token if we have one
                if self.auth_token:
                    self._refresh_token()
                    return self._request(method, endpoint, params, data, headers)
                return None
            elif response.status_code == 404:
                log(f"Endpoint not found: {endpoint}", xbmc.LOGWARNING)
                return None
            else:
                log(f"API Error {response.status_code}: {response.text}", xbmc.LOGERROR)
                return None
                
        except requests.exceptions.RequestException as e:
            log(f"Request error: {str(e)}", xbmc.LOGERROR)
            return None
        except json.JSONDecodeError as e:
            log(f"JSON decode error: {str(e)}", xbmc.LOGERROR)
            return None
    
    def _refresh_token(self):
        """Refresh authentication token"""
        # This would implement token refresh logic
        # For now, we'll just clear the token
        self.auth_token = ''
        set_setting('auth_token', '')
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        return False
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return bool(self.auth_token)
    
    def get_categories(self, content_type='all'):
        """Get available categories"""
        cache_key = f'categories_{content_type}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/categories'
        if content_type != 'all':
            endpoint += f'?type={content_type}'
        
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            categories = data['data']
            cache_set(cache_key, categories, 3600)  # Cache for 1 hour
            return categories
        
        # Fallback categories
        fallback = [
            {'id': 'featured', 'name': 'Featured', 'type': 'all'},
            {'id': 'popular', 'name': 'Popular', 'type': 'all'},
            {'id': 'action', 'name': 'Action', 'type': 'movies'},
            {'id': 'comedy', 'name': 'Comedy', 'type': 'all'},
            {'id': 'drama', 'name': 'Drama', 'type': 'all'},
            {'id': 'horror', 'name': 'Horror', 'type': 'movies'},
            {'id': 'scifi', 'name': 'Sci-Fi', 'type': 'all'},
            {'id': 'documentary', 'name': 'Documentary', 'type': 'all'}
        ]
        return fallback
    
    def get_movies(self, category='featured', page=1, limit=20):
        """Get movies by category"""
        cache_key = f'movies_{category}_{page}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/movies'
        params = {
            'category': category,
            'page': page,
            'limit': limit
        }
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            movies = self._parse_movies(data['data'])
            cache_set(cache_key, movies, 300)  # Cache for 5 minutes
            return movies
        
        # Mock data for development
        return self._get_mock_movies(category, page)
    
    def get_tv_shows(self, category='featured', page=1, limit=20):
        """Get TV shows by category"""
        cache_key = f'tvshows_{category}_{page}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = '/tv-shows'
        params = {
            'category': category,
            'page': page,
            'limit': limit
        }
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            shows = self._parse_tv_shows(data['data'])
            cache_set(cache_key, shows, 300)
            return shows
        
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
        
        return [{'number': 1, 'description': 'Season 1'}]
    
    def get_episodes(self, show_id, season_number):
        """Get episodes for a specific season"""
        cache_key = f'episodes_{show_id}_{season_number}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = f'/tv-shows/{show_id}/seasons/{season_number}/episodes'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            episodes = self._parse_episodes(data['data'])
            cache_set(cache_key, episodes, 3600)
            return episodes
        
        return self._get_mock_episodes(show_id, season_number)
    
    def get_stream_url(self, video_id):
        """Get video stream URL with DRM information"""
        cache_key = f'stream_{video_id}'
        cached = cache_get(cache_key)
        if cached:
            return cached
        
        endpoint = f'/video/{video_id}/stream'
        
        # Add device info
        headers = {
            'X-Device-Id': self._get_device_id(),
            'X-Platform': 'web',
            'X-App-Version': '3.0.0'
        }
        
        data = self._request('GET', endpoint, headers=headers)
        
        if data and data.get('data'):
            stream_data = {
                'url': data['data'].get('url'),
                'license_url': data['data'].get('license_url'),
                'manifest_type': data['data'].get('manifest_type', 'hls'),
                'drm_type': data['data'].get('drm_type', 'widevine')
            }
            cache_set(cache_key, stream_data, 3600)
            return stream_data
        
        # Mock stream data for development
        return {
            'url': f'https://example.com/stream/{video_id}.m3u8',
            'license_url': 'https://example.com/license',
            'manifest_type': 'hls',
            'drm_type': 'widevine'
        }
    
    def search(self, query, page=1, limit=20):
        """Search for content"""
        endpoint = '/search'
        params = {
            'q': query,
            'page': page,
            'limit': limit
        }
        
        data = self._request('GET', endpoint, params=params)
        
        if data and data.get('data'):
            return self._parse_search_results(data['data'])
        
        return []
    
    def get_my_list(self):
        """Get user's saved list"""
        if not self.is_authenticated():
            return []
        
        endpoint = '/user/list'
        data = self._request('GET', endpoint)
        
        if data and data.get('data'):
            return self._parse_my_list(data['data'])
        
        return []
    
    def login(self, email, password):
        """Authenticate user"""
        endpoint = '/auth/login'
        data = {
            'email': email,
            'password': password
        }
        
        response = self._request('POST', endpoint, data=data)
        
        if response and response.get('data'):
            auth_data = response['data']
            self.auth_token = auth_data.get('token')
            self.user_id = auth_data.get('user_id')
            
            if self.auth_token:
                set_setting('auth_token', self.auth_token)
                set_setting('user_id', self.user_id)
                self.session.headers['Authorization'] = f'Bearer {self.auth_token}'
                return True
        
        return False
    
    def _get_device_id(self):
        """Generate or get device ID"""
        device_id = get_setting('device_id')
        if not device_id:
            # Generate a random device ID
            import uuid
            device_id = str(uuid.uuid4())
            set_setting('device_id', device_id)
        return device_id
    
    def _parse_movies(self, data):
        """Parse movie data from API response"""
        movies = []
        for item in data:
            movies.append({
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'thumbnail': item.get('thumbnail', ''),
                'background': item.get('background', ''),
                'year': item.get('year'),
                'duration': item.get('duration', 0),
                'genres': item.get('genres', []),
                'rating': item.get('rating', 0),
                'content_rating': item.get('content_rating', ''),
                'type': 'movie'
            })
        return movies
    
    def _parse_tv_shows(self, data):
        """Parse TV show data from API response"""
        shows = []
        for item in data:
            shows.append({
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'thumbnail': item.get('thumbnail', ''),
                'background': item.get('background', ''),
                'year': item.get('year'),
                'genres': item.get('genres', []),
                'rating': item.get('rating', 0),
                'type': 'tvshow'
            })
        return shows
    
    def _parse_episodes(self, data):
        """Parse episode data from API response"""
        episodes = []
        for item in data:
            episodes.append({
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'thumbnail': item.get('thumbnail', ''),
                'background': item.get('background', ''),
                'duration': item.get('duration', 0),
                'episode_number': item.get('episode_number', 0),
                'season_number': item.get('season_number', 1),
                'rating': item.get('rating', 0),
                'type': 'episode'
            })
        return episodes
    
    def _parse_search_results(self, data):
        """Parse search results from API response"""
        results = []
        for item in data:
            result = {
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'thumbnail': item.get('thumbnail', ''),
                'background': item.get('background', ''),
                'year': item.get('year'),
                'type': item.get('type', 'movie')
            }
            results.append(result)
        return results
    
    def _parse_my_list(self, data):
        """Parse my list data from API response"""
        items = []
        for item in data:
            items.append({
                'id': item.get('id'),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'thumbnail': item.get('thumbnail', ''),
                'type': item.get('type', 'movie')
            })
        return items
    
    # Mock data for development when API is not available
    def _get_mock_movies(self, category, page):
        """Generate mock movie data for development"""
        movies = []
        for i in range(1, 21):
            movies.append({
                'id': f'movie_{i}',
                'title': f'Movie {i} - {category}',
                'description': f'This is a description for movie {i} in the {category} category.',
                'thumbnail': 'https://via.placeholder.com/300x450',
                'background': 'https://via.placeholder.com/1920x1080',
                'year': 2020 + (i % 5),
                'duration': 90 + (i % 60),
                'genres': ['Action', 'Drama'],
                'rating': 4 + (i % 1),
                'content_rating': 'PG-13',
                'type': 'movie'
            })
        return movies
    
    def _get_mock_tv_shows(self, category, page):
        """Generate mock TV show data for development"""
        shows = []
        for i in range(1, 21):
            shows.append({
                'id': f'show_{i}',
                'title': f'TV Show {i} - {category}',
                'description': f'This is a description for TV show {i} in the {category} category.',
                'thumbnail': 'https://via.placeholder.com/300x450',
                'background': 'https://via.placeholder.com/1920x1080',
                'year': 2020 + (i % 4),
                'genres': ['Drama', 'Comedy'],
                'rating': 4 + (i % 1),
                'type': 'tvshow'
            })
        return shows
    
    def _get_mock_episodes(self, show_id, season_number):
        """Generate mock episode data for development"""
        episodes = []
        for i in range(1, 11):
            episodes.append({
                'id': f'episode_{i}',
                'title': f'Episode {i}',
                'description': f'Description for episode {i} of season {season_number}',
                'thumbnail': 'https://via.placeholder.com/300x450',
                'background': 'https://via.placeholder.com/1920x1080',
                'duration': 45,
                'episode_number': i,
                'season_number': season_number,
                'rating': 4 + (i % 1),
                'type': 'episode'
            })
        return episodes
