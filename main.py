# -*- coding: utf-8 -*-
"""
Tubi TV Kodi Add-on
Main entry point
"""

import sys
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
from urllib.parse import parse_qsl, urlencode

# Import our modules
from resources.lib.tubi_api import TubiAPI
from resources.lib.utils import log, get_setting, set_setting
from resources.lib.player import TubiPlayer

# Add-on constants
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_VERSION = ADDON.getAddonInfo('version')
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

# Localization function
def _(text_id):
    return ADDON.getLocalizedString(text_id)

# Route parameters
def get_params(param_string):
    """Parse URL parameters into a dictionary"""
    if param_string.startswith('?'):
        param_string = param_string[1:]
    return dict(parse_qsl(param_string))

# Main router
def router(param_string):
    """Route to the appropriate function based on URL parameters"""
    params = get_params(param_string)
    mode = params.get('mode', 'list_categories')
    
    log(f"Router mode: {mode}, params: {params}")
    
    # Initialize API and player
    api = TubiAPI()
    player = TubiPlayer()
    
    if mode == 'list_categories':
        list_categories(api)
    elif mode == 'list_movies':
        list_movies(api, params)
    elif mode == 'list_tvshows':
        list_tvshows(api, params)
    elif mode == 'list_seasons':
        list_seasons(api, params)
    elif mode == 'list_episodes':
        list_episodes(api, params)
    elif mode == 'play':
        play_video(player, api, params)
    elif mode == 'search':
        search_content(api, params)
    elif mode == 'my_list':
        my_list(api, params)
    elif mode == 'login':
        login(api)
    elif mode == 'logout':
        logout()
    elif mode == 'clear_cache':
        clear_cache()
    else:
        # Default to categories
        list_categories(api)
    
    # Add sorting methods
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    
    # End of directory
    xbmcplugin.endOfDirectory(HANDLE)

def build_url(query):
    """Build a URL with query parameters"""
    return BASE_URL + '?' + urlencode(query)

def list_categories(api):
    """Display main categories"""
    log("Listing categories")
    
    # Main menu items
    categories = [
        {
            'title': _(30001),  # Movies
            'mode': 'list_movies',
            'category': 'movies',
            'icon': 'DefaultMovies.png'
        },
        {
            'title': _(30002),  # TV Shows
            'mode': 'list_tvshows',
            'category': 'tvshows',
            'icon': 'DefaultTVShows.png'
        },
        {
            'title': _(30003),  # My List
            'mode': 'my_list',
            'category': 'mylist',
            'icon': 'DefaultFavourites.png'
        },
        {
            'title': _(30004),  # Search
            'mode': 'search',
            'icon': 'DefaultSearch.png'
        }
    ]
    
    # Add login/logout based on auth status
    if api.is_authenticated():
        categories.append({
            'title': _(30006),  # Logout
            'mode': 'logout',
            'icon': 'DefaultSettings.png'
        })
    else:
        categories.append({
            'title': _(30005),  # Login
            'mode': 'login',
            'icon': 'DefaultUser.png'
        })
    
    # Add settings
    categories.append({
        'title': 'Settings',
        'mode': 'settings',
        'icon': 'DefaultSettings.png'
    })
    
    for item in categories:
        list_item = xbmcgui.ListItem(label=item['title'])
        
        if item.get('icon'):
            list_item.setArt({'icon': item['icon']})
        
        if item['mode'] == 'settings':
            # Open Kodi addon settings
            url = 'plugin://' + ADDON_ID + '/settings'
        else:
            url = build_url({'mode': item['mode'], 'category': item.get('category', '')})
        
        xbmcplugin.addDirectoryItem(
            handle=HANDLE,
            url=url,
            listitem=list_item,
            isFolder=True
        )

def list_movies(api, params):
    """Display movie listings"""
    log(f"Listing movies with params: {params}")
    
    # Get movies from API
    category = params.get('category', 'featured')
    page = int(params.get('page', 1))
    
    # Show loading indicator
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        movies = api.get_movies(category, page)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        for movie in movies:
            list_item = xbmcgui.ListItem(label=movie['title'])
            
            # Set artwork
            list_item.setArt({
                'thumb': movie.get('thumbnail', ''),
                'fanart': movie.get('background', ''),
                'poster': movie.get('thumbnail', '')
            })
            
            # Set video info
            info = {
                'title': movie.get('title', ''),
                'plot': movie.get('description', ''),
                'year': movie.get('year', ''),
                'duration': movie.get('duration', 0),
                'genre': ', '.join(movie.get('genres', [])),
                'rating': movie.get('rating', 0),
                'studio': 'Tubi TV',
                'mpaa': movie.get('content_rating', '')
            }
            list_item.setInfo('video', info)
            
            # Add play url
            url = build_url({
                'mode': 'play',
                'video_id': movie.get('id'),
                'title': movie.get('title', ''),
                'thumbnail': movie.get('thumbnail', ''),
                'description': movie.get('description', '')
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=False
            )
        
        # Add pagination
        if movies and len(movies) >= 20:
            next_page = page + 1
            list_item = xbmcgui.ListItem(label=f"Next Page ►")
            list_item.setArt({'icon': 'DefaultFolder.png'})
            url = build_url({
                'mode': 'list_movies',
                'category': category,
                'page': next_page
            })
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error listing movies: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def list_tvshows(api, params):
    """Display TV show listings"""
    log(f"Listing TV shows with params: {params}")
    
    category = params.get('category', 'featured')
    page = int(params.get('page', 1))
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        shows = api.get_tv_shows(category, page)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        for show in shows:
            list_item = xbmcgui.ListItem(label=show['title'])
            
            list_item.setArt({
                'thumb': show.get('thumbnail', ''),
                'fanart': show.get('background', ''),
                'poster': show.get('thumbnail', '')
            })
            
            info = {
                'title': show.get('title', ''),
                'plot': show.get('description', ''),
                'year': show.get('year', ''),
                'genre': ', '.join(show.get('genres', [])),
                'rating': show.get('rating', 0),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            url = build_url({
                'mode': 'list_seasons',
                'show_id': show.get('id'),
                'title': show.get('title', ''),
                'thumbnail': show.get('thumbnail', '')
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )
        
        if shows and len(shows) >= 20:
            next_page = page + 1
            list_item = xbmcgui.ListItem(label=f"Next Page ►")
            url = build_url({
                'mode': 'list_tvshows',
                'category': category,
                'page': next_page
            })
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error listing TV shows: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def list_seasons(api, params):
    """Display seasons for a TV show"""
    log(f"Listing seasons with params: {params}")
    
    show_id = params.get('show_id')
    title = params.get('title', '')
    thumbnail = params.get('thumbnail', '')
    
    if not show_id:
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        seasons = api.get_seasons(show_id)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        for season in seasons:
            list_item = xbmcgui.ListItem(label=f"Season {season.get('number', '')}")
            
            list_item.setArt({
                'thumb': thumbnail,
                'poster': thumbnail
            })
            
            info = {
                'title': f"{title} - Season {season.get('number', '')}",
                'plot': season.get('description', ''),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            url = build_url({
                'mode': 'list_episodes',
                'show_id': show_id,
                'season': season.get('number', 1),
                'title': title,
                'thumbnail': thumbnail
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error listing seasons: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def list_episodes(api, params):
    """Display episodes for a season"""
    log(f"Listing episodes with params: {params}")
    
    show_id = params.get('show_id')
    season = int(params.get('season', 1))
    title = params.get('title', '')
    thumbnail = params.get('thumbnail', '')
    
    if not show_id:
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        episodes = api.get_episodes(show_id, season)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        for episode in episodes:
            list_item = xbmcgui.ListItem(label=episode.get('title', ''))
            
            list_item.setArt({
                'thumb': episode.get('thumbnail', thumbnail),
                'fanart': episode.get('background', ''),
                'poster': episode.get('thumbnail', thumbnail)
            })
            
            info = {
                'title': episode.get('title', ''),
                'plot': episode.get('description', ''),
                'duration': episode.get('duration', 0),
                'episode': episode.get('episode_number', 0),
                'season': season,
                'studio': 'Tubi TV',
                'rating': episode.get('rating', 0)
            }
            list_item.setInfo('video', info)
            
            url = build_url({
                'mode': 'play',
                'video_id': episode.get('id'),
                'title': episode.get('title', ''),
                'thumbnail': episode.get('thumbnail', thumbnail),
                'description': episode.get('description', ''),
                'season': season,
                'episode': episode.get('episode_number', 0)
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=False
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error listing episodes: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def play_video(player, api, params):
    """Play a video"""
    log(f"Playing video with params: {params}")
    
    video_id = params.get('video_id')
    title = params.get('title', '')
    thumbnail = params.get('thumbnail', '')
    description = params.get('description', '')
    season = params.get('season', '')
    episode = params.get('episode', '')
    
    if not video_id:
        xbmcgui.Dialog().ok(ADDON_NAME, "No video ID provided")
        return
    
    try:
        # Get stream URL from API
        stream_data = api.get_stream_url(video_id)
        
        if not stream_data:
            xbmcgui.Dialog().ok(ADDON_NAME, "Could not get stream URL")
            return
        
        # Play the video
        player.play_video(
            video_id=video_id,
            stream_url=stream_data.get('url'),
            title=title,
            thumbnail=thumbnail,
            description=description,
            season=season,
            episode=episode,
            license_url=stream_data.get('license_url'),
            manifest_type=stream_data.get('manifest_type', 'hls')
        )
        
    except Exception as e:
        log(f"Error playing video: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Error playing video: {str(e)}")

def search_content(api, params):
    """Search for content"""
    log(f"Search with params: {params}")
    
    query = params.get('query', '')
    
    if not query:
        # Show keyboard dialog
        kb = xbmc.Keyboard('', 'Search Tubi TV')
        kb.doModal()
        if kb.isConfirmed():
            query = kb.getText()
        else:
            return
    
    if not query:
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        results = api.search(query)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not results:
            xbmcgui.Dialog().ok(ADDON_NAME, "No results found")
            return
        
        for item in results:
            list_item = xbmcgui.ListItem(label=item['title'])
            
            list_item.setArt({
                'thumb': item.get('thumbnail', ''),
                'fanart': item.get('background', ''),
                'poster': item.get('thumbnail', '')
            })
            
            info = {
                'title': item.get('title', ''),
                'plot': item.get('description', ''),
                'year': item.get('year', ''),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            if item.get('type') == 'movie':
                url = build_url({
                    'mode': 'play',
                    'video_id': item.get('id'),
                    'title': item.get('title', ''),
                    'thumbnail': item.get('thumbnail', ''),
                    'description': item.get('description', '')
                })
                is_folder = False
            else:  # TV show
                url = build_url({
                    'mode': 'list_seasons',
                    'show_id': item.get('id'),
                    'title': item.get('title', ''),
                    'thumbnail': item.get('thumbnail', '')
                })
                is_folder = True
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=is_folder
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error searching: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def my_list(api, params):
    """Display user's saved list"""
    log("Accessing My List")
    
    if not api.is_authenticated():
        xbmcgui.Dialog().ok(ADDON_NAME, "Please login first to access My List")
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        items = api.get_my_list()
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        for item in items:
            list_item = xbmcgui.ListItem(label=item['title'])
            
            list_item.setArt({
                'thumb': item.get('thumbnail', ''),
                'poster': item.get('thumbnail', '')
            })
            
            info = {
                'title': item.get('title', ''),
                'plot': item.get('description', ''),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            if item.get('type') == 'movie':
                url = build_url({
                    'mode': 'play',
                    'video_id': item.get('id'),
                    'title': item.get('title', ''),
                    'thumbnail': item.get('thumbnail', '')
                })
                is_folder = False
            else:
                url = build_url({
                    'mode': 'list_seasons',
                    'show_id': item.get('id'),
                    'title': item.get('title', ''),
                    'thumbnail': item.get('thumbnail', '')
                })
                is_folder = True
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=is_folder
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error loading My List: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Error loading My List")

def login(api):
    """Handle user login"""
    log("Login requested")
    
    # Get credentials from user
    email = xbmcgui.Dialog().input(_(30008), type=xbmcgui.INPUT_ALPHANUM)
    if not email:
        return
    
    password = xbmcgui.Dialog().input(_(30009), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        success = api.login(email, password)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if success:
            set_setting('username', email)
            xbmcgui.Dialog().ok(ADDON_NAME, "Login successful!")
            # Refresh the menu
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().ok(ADDON_NAME, "Login failed. Please check your credentials.")
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error during login: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Login error. Please try again.")

def logout():
    """Handle user logout"""
    log("Logout requested")
    
    if xbmcgui.Dialog().yesno(ADDON_NAME, "Are you sure you want to logout?"):
        set_setting('username', '')
        set_setting('auth_token', '')
        xbmcgui.Dialog().ok(ADDON_NAME, "Logged out successfully")
        # Refresh the menu
        xbmc.executebuiltin('Container.Refresh')

def clear_cache():
    """Clear cached data"""
    log("Clearing cache")
    from resources.lib.utils import clear_cache as clear_cache_util
    clear_cache_util()
    xbmcgui.Dialog().ok(ADDON_NAME, "Cache cleared successfully")

# Run the router
if __name__ == '__main__':
    param_string = sys.argv[2][1:] if len(sys.argv) > 2 else ''
    router(param_string)
