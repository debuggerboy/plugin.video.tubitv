# -*- coding: utf-8 -*-
"""
Tubi TV Kodi Add-on
Main entry point - Enhanced with comprehensive navigation and features
"""

import sys
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
from urllib.parse import parse_qsl, urlencode

# Import our modules
from resources.lib.tubi_api import TubiAPI
from resources.lib.utils import log, get_setting, set_setting, clear_cache
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

def build_url(query):
    """Build a URL with query parameters"""
    return BASE_URL + '?' + urlencode(query)

# Main router
def router(param_string):
    """Route to the appropriate function based on URL parameters"""
    params = get_params(param_string)
    mode = params.get('mode', 'list_categories')
    
    log(f"Router mode: {mode}, params: {params}")
    
    # Initialize API and player
    api = TubiAPI()
    player = TubiPlayer()
    
    # Route to appropriate function
    if mode == 'list_categories':
        list_categories(api)
    elif mode == 'list_home':
        list_home(api)
    elif mode == 'list_movies':
        list_movies(api, params)
    elif mode == 'list_tvshows':
        list_tvshows(api, params)
    elif mode == 'list_seasons':
        list_seasons(api, params)
    elif mode == 'list_episodes':
        list_episodes(api, params)
    elif mode == 'list_genres':
        list_genres(api, params)
    elif mode == 'list_by_genre':
        list_by_genre(api, params)
    elif mode == 'play':
        play_video(player, api, params)
    elif mode == 'search':
        search_content(api, params)
    elif mode == 'search_suggestions':
        search_suggestions(api, params)
    elif mode == 'my_list':
        my_list(api, params)
    elif mode == 'add_to_list':
        add_to_list(api, params)
    elif mode == 'remove_from_list':
        remove_from_list(api, params)
    elif mode == 'watch_history':
        watch_history(api)
    elif mode == 'login':
        login(api)
    elif mode == 'logout':
        logout()
    elif mode == 'clear_cache':
        clear_cache_dialog()
    elif mode == 'settings':
        ADDON.openSettings()
    elif mode == 'content_details':
        content_details(api, params)
    else:
        # Default to categories
        list_categories(api)
    
    # Add sorting methods for content lists
    if mode in ['list_movies', 'list_tvshows', 'list_by_genre', 'search']:
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_RATING)
    
    # End of directory
    xbmcplugin.endOfDirectory(HANDLE)

# ============ Navigation Functions ============

def list_categories(api):
    """Display main categories with enhanced menu"""
    log("Listing categories")
    
    # Main menu items with icons
    categories = [
        {
            'title': 'Home',
            'mode': 'list_home',
            'icon': 'DefaultHome.png'
        },
        {
            'title': _(30001),  # Movies
            'mode': 'list_movies',
            'category': 'featured',
            'icon': 'DefaultMovies.png'
        },
        {
            'title': _(30002),  # TV Shows
            'mode': 'list_tvshows',
            'category': 'featured',
            'icon': 'DefaultTVShows.png'
        },
        {
            'title': 'Genres',
            'mode': 'list_genres',
            'icon': 'DefaultGenre.png'
        },
        {
            'title': _(30003),  # My List
            'mode': 'my_list',
            'icon': 'DefaultFavourites.png'
        },
        {
            'title': 'Watch History',
            'mode': 'watch_history',
            'icon': 'DefaultRecentlyAdded.png'
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
    
    # Add settings and utilities
    categories.extend([
        {
            'title': 'Clear Cache',
            'mode': 'clear_cache',
            'icon': 'DefaultAddonTools.png'
        },
        {
            'title': 'Settings',
            'mode': 'settings',
            'icon': 'DefaultAddonSettings.png'
        }
    ])
    
    for item in categories:
        list_item = xbmcgui.ListItem(label=item['title'])
        
        if item.get('icon'):
            list_item.setArt({'icon': item['icon']})
        
        # Build URL
        url_params = {'mode': item['mode']}
        if item.get('category'):
            url_params['category'] = item['category']
        
        url = build_url(url_params)
        
        # Determine if folder
        is_folder = item['mode'] not in ['play', 'logout', 'clear_cache', 'settings']
        
        xbmcplugin.addDirectoryItem(
            handle=HANDLE,
            url=url,
            listitem=list_item,
            isFolder=is_folder
        )

def list_home(api):
    """Display home page with featured content"""
    log("Listing home page")
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        home_data = api.get_home_page()
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not home_data:
            xbmcgui.Dialog().ok(ADDON_NAME, "Could not load home page")
            return
        
        # Display featured content
        if 'featured' in home_data:
            add_content_section(api, "Featured", home_data['featured'])
        
        if 'trending' in home_data:
            add_content_section(api, "Trending", home_data['trending'])
        
        if 'popular' in home_data:
            add_content_section(api, "Popular", home_data['popular'])
        
        # Add genre shortcuts
        if 'genres' in home_data:
            list_item = xbmcgui.ListItem(label="Browse All Genres")
            list_item.setArt({'icon': 'DefaultGenre.png'})
            url = build_url({'mode': 'list_genres'})
            xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error loading home page: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def add_content_section(api, title, content_items):
    """Add a section of content to the directory"""
    if not content_items:
        return
    
    # Add section header
    list_item = xbmcgui.ListItem(label=f"--- {title} ---")
    list_item.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(HANDLE, '', list_item, False)
    
    # Add content items
    for item in content_items[:10]:  # Limit to 10 items per section
        add_content_item(api, item, title)

def add_content_item(api, item, section_title=""):
    """Add a single content item to the directory"""
    title = item.get('title', 'Unknown')
    content_id = item.get('id')
    content_type = item.get('type', 'movie')
    thumbnail = item.get('thumbnail') or item.get('poster', '')
    
    list_item = xbmcgui.ListItem(label=title)
    
    # Set artwork
    list_item.setArt({
        'thumb': thumbnail,
        'poster': thumbnail,
        'fanart': item.get('background') or item.get('fanart', '')
    })
    
    # Set video info
    info = {
        'title': title,
        'plot': item.get('description') or item.get('plot', ''),
        'year': item.get('year'),
        'rating': item.get('rating', 0),
        'studio': 'Tubi TV'
    }
    list_item.setInfo('video', info)
    
    # Determine URL based on content type
    if content_type == 'movie':
        url = build_url({
            'mode': 'play',
            'video_id': content_id,
            'title': title,
            'thumbnail': thumbnail,
            'description': item.get('description', '')
        })
        is_folder = False
    else:  # TV show
        url = build_url({
            'mode': 'list_seasons',
            'show_id': content_id,
            'title': title,
            'thumbnail': thumbnail
        })
        is_folder = True
    
    xbmcplugin.addDirectoryItem(
        handle=HANDLE,
        url=url,
        listitem=list_item,
        isFolder=is_folder
    )

def list_movies(api, params):
    """Display movie listings with filtering"""
    log(f"Listing movies with params: {params}")
    
    category = params.get('category', 'featured')
    page = int(params.get('page', 1))
    sort_by = params.get('sort_by', '')
    
    # Add sorting options
    if page == 1:
        add_sort_options('list_movies', {'category': category})
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        movies = api.get_movies(category, page, sort_by=sort_by)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not movies:
            xbmcgui.Dialog().ok(ADDON_NAME, "No movies found in this category")
            return
        
        for movie in movies:
            list_item = xbmcgui.ListItem(label=movie['title'])
            
            # Set artwork
            list_item.setArt({
                'thumb': movie.get('thumbnail', ''),
                'poster': movie.get('poster', movie.get('thumbnail', '')),
                'fanart': movie.get('fanart', movie.get('background', ''))
            })
            
            # Set video info with full metadata
            info = {
                'title': movie.get('title', ''),
                'plot': movie.get('plot', movie.get('description', '')),
                'year': movie.get('year', ''),
                'duration': movie.get('duration', 0),
                'genre': ', '.join(movie.get('genres', [])),
                'rating': movie.get('rating', 0),
                'studio': 'Tubi TV',
                'mpaa': movie.get('mpaa', movie.get('content_rating', ''))
            }
            list_item.setInfo('video', info)
            
            # Add context menu
            context_menu = []
            if api.is_authenticated():
                context_menu.append((
                    'Add to My List',
                    f'RunPlugin({build_url({"mode": "add_to_list", "content_id": movie["id"], "content_type": "movie", "title": movie["title"]})})'
                ))
            list_item.addContextMenuItems(context_menu)
            
            # Add play url
            url = build_url({
                'mode': 'play',
                'video_id': movie['id'],
                'title': movie['title'],
                'thumbnail': movie.get('thumbnail', ''),
                'description': movie.get('plot', movie.get('description', ''))
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=False
            )
        
        # Add pagination
        add_pagination('list_movies', {'category': category, 'sort_by': sort_by}, page)
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error listing movies: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def list_tvshows(api, params):
    """Display TV show listings"""
    log(f"Listing TV shows with params: {params}")
    
    category = params.get('category', 'featured')
    page = int(params.get('page', 1))
    sort_by = params.get('sort_by', '')
    
    if page == 1:
        add_sort_options('list_tvshows', {'category': category})
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        shows = api.get_tv_shows(category, page, sort_by=sort_by)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not shows:
            xbmcgui.Dialog().ok(ADDON_NAME, "No TV shows found in this category")
            return
        
        for show in shows:
            list_item = xbmcgui.ListItem(label=show['title'])
            
            list_item.setArt({
                'thumb': show.get('thumbnail', ''),
                'poster': show.get('poster', show.get('thumbnail', '')),
                'fanart': show.get('fanart', show.get('background', ''))
            })
            
            info = {
                'title': show.get('title', ''),
                'plot': show.get('plot', show.get('description', '')),
                'year': show.get('year', ''),
                'genre': ', '.join(show.get('genres', [])),
                'rating': show.get('rating', 0),
                'studio': 'Tubi TV',
                'episode_count': show.get('episode_count', 0)
            }
            list_item.setInfo('video', info)
            
            # Add context menu
            context_menu = []
            if api.is_authenticated():
                context_menu.append((
                    'Add to My List',
                    f'RunPlugin({build_url({"mode": "add_to_list", "content_id": show["id"], "content_type": "tvshow", "title": show["title"]})})'
                ))
            list_item.addContextMenuItems(context_menu)
            
            url = build_url({
                'mode': 'list_seasons',
                'show_id': show['id'],
                'title': show['title'],
                'thumbnail': show.get('thumbnail', '')
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )
        
        # Add pagination
        add_pagination('list_tvshows', {'category': category, 'sort_by': sort_by}, page)
            
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
        
        if not seasons:
            xbmcgui.Dialog().ok(ADDON_NAME, "No seasons found for this show")
            return
        
        # Add show details option
        details_item = xbmcgui.ListItem(label="Show Details")
        details_item.setArt({'icon': 'DefaultInfo.png'})
        url = build_url({
            'mode': 'content_details',
            'content_id': show_id,
            'content_type': 'tvshow',
            'title': title
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, details_item, True)
        
        for season in seasons:
            season_num = season.get('number', season.get('season_number', 1))
            season_title = f"Season {season_num}"
            if season.get('description'):
                season_title += f" - {season['description']}"
            
            list_item = xbmcgui.ListItem(label=season_title)
            
            list_item.setArt({
                'thumb': thumbnail,
                'poster': thumbnail
            })
            
            info = {
                'title': f"{title} - Season {season_num}",
                'plot': season.get('description', ''),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            url = build_url({
                'mode': 'list_episodes',
                'show_id': show_id,
                'season': season_num,
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
        
        if not episodes:
            xbmcgui.Dialog().ok(ADDON_NAME, "No episodes found for this season")
            return
        
        for episode in episodes:
            episode_title = f"{episode.get('episode_number', 0)}. {episode.get('title', '')}"
            if episode.get('duration'):
                duration_min = int(episode['duration'] / 60)
                episode_title += f" ({duration_min}m)"
            
            list_item = xbmcgui.ListItem(label=episode_title)
            
            list_item.setArt({
                'thumb': episode.get('thumbnail', thumbnail),
                'poster': episode.get('poster', thumbnail),
                'fanart': episode.get('fanart', '')
            })
            
            info = {
                'title': episode.get('title', ''),
                'plot': episode.get('plot', episode.get('description', '')),
                'duration': episode.get('duration', 0),
                'episode': episode.get('episode_number', 0),
                'season': season,
                'studio': 'Tubi TV',
                'rating': episode.get('rating', 0),
                'aired': episode.get('aired', '')
            }
            list_item.setInfo('video', info)
            
            # Add play count and resume if available
            if episode.get('progress'):
                list_item.setProperty('resume_time', str(episode['progress']))
                list_item.setProperty('total_time', str(episode.get('duration', 0)))
            
            url = build_url({
                'mode': 'play',
                'video_id': episode['id'],
                'title': episode.get('title', ''),
                'thumbnail': episode.get('thumbnail', thumbnail),
                'description': episode.get('plot', episode.get('description', '')),
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

def list_genres(api, params):
    """Display available genres"""
    log("Listing genres")
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        categories = api.get_categories()
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        # Filter to show only genre categories
        genres = [cat for cat in categories if cat.get('type') != 'all']
        
        if not genres:
            # Fallback genres
            genres = [
                {'id': 'action', 'name': 'Action'},
                {'id': 'comedy', 'name': 'Comedy'},
                {'id': 'drama', 'name': 'Drama'},
                {'id': 'horror', 'name': 'Horror'},
                {'id': 'sci-fi', 'name': 'Sci-Fi'},
                {'id': 'thriller', 'name': 'Thriller'},
                {'id': 'romance', 'name': 'Romance'},
                {'id': 'documentary', 'name': 'Documentary'},
                {'id': 'reality', 'name': 'Reality'},
                {'id': 'kids', 'name': 'Kids & Family'},
                {'id': 'anime', 'name': 'Anime'}
            ]
        
        for genre in genres:
            genre_name = genre.get('name', genre.get('title', 'Unknown'))
            genre_id = genre.get('id', genre_name.lower())
            
            list_item = xbmcgui.ListItem(label=genre_name)
            list_item.setArt({'icon': 'DefaultGenre.png'})
            
            url = build_url({
                'mode': 'list_by_genre',
                'genre': genre_id,
                'genre_name': genre_name
            })
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error listing genres: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Error loading genres")

def list_by_genre(api, params):
    """List content by genre"""
    genre = params.get('genre')
    genre_name = params.get('genre_name', genre)
    
    # Add movies and TV shows by genre
    list_item = xbmcgui.ListItem(label=f"Movies - {genre_name}")
    list_item.setArt({'icon': 'DefaultMovies.png'})
    url = build_url({
        'mode': 'list_movies',
        'category': genre,
        'sort_by': 'popular'
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)
    
    list_item = xbmcgui.ListItem(label=f"TV Shows - {genre_name}")
    list_item.setArt({'icon': 'DefaultTVShows.png'})
    url = build_url({
        'mode': 'list_tvshows',
        'category': genre,
        'sort_by': 'popular'
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)

def content_details(api, params):
    """Display detailed information about content"""
    content_id = params.get('content_id')
    content_type = params.get('content_type', 'movie')
    title = params.get('title', '')
    
    if not content_id:
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        details = api.get_content_details(content_id, content_type)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not details:
            xbmcgui.Dialog().ok(ADDON_NAME, "Could not load content details")
            return
        
        # Display details in a dialog
        info_text = f"[B]Title:[/B] {details.get('title', title)}\n"
        info_text += f"[B]Year:[/B] {details.get('year', 'N/A')}\n"
        info_text += f"[B]Rating:[/B] {details.get('rating', 'N/A')}\n"
        info_text += f"[B]Genres:[/B] {', '.join(details.get('genres', []))}\n"
        info_text += f"[B]Duration:[/B] {details.get('duration', 'N/A')} minutes\n"
        
        if details.get('cast'):
            cast_list = details['cast'][:5]
            info_text += f"[B]Cast:[/B] {', '.join(cast_list)}\n"
        
        if details.get('plot'):
            info_text += f"\n[B]Plot:[/B]\n{details.get('plot', '')}"
        
        xbmcgui.Dialog().textviewer(title, info_text)
        
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error loading content details: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Error loading content details")

# ============ Playback Functions ============

def play_video(player, api, params):
    """Play a video with full support for DRM and ads"""
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
        
        # Prepare metadata for player
        metadata = {
            'plot': description,
            'fanart': params.get('fanart', ''),
            'banner': params.get('banner', '')
        }
        
        # Get ad cue points if available
        ad_cue_points = stream_data.get('cue_points', stream_data.get('ad_breaks', []))
        
        # Get subtitles if available
        subtitles = stream_data.get('subtitles', [])
        
        # Get audio tracks if available
        audio_tracks = stream_data.get('audio_tracks', [])
        
        # Play the video
        player.play_video(
            video_id=video_id,
            stream_url=stream_data.get('manifest_url') or stream_data.get('url'),
            title=title,
            thumbnail=thumbnail,
            description=metadata,
            season=season,
            episode=episode,
            license_url=stream_data.get('license_url'),
            manifest_type=stream_data.get('manifest_type', 'hls'),
            drm_type=stream_data.get('drm_type', 'widevine'),
            headers=stream_data.get('headers', {}),
            ad_cue_points=ad_cue_points,
            subtitles=subtitles,
            audio_tracks=audio_tracks,
            duration=stream_data.get('duration', 0)
        )
        
        # Update watch progress if authenticated
        if api.is_authenticated():
            # Start progress tracking
            track_progress(api, video_id, title, season, episode)
        
    except Exception as e:
        log(f"Error playing video: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Error playing video: {str(e)}")

def track_progress(api, video_id, title, season, episode):
    """Track playback progress for authenticated users"""
    log(f"Tracking progress for: {title}")
    
    # Set up progress tracking in a separate thread
    import threading
    
    def progress_tracker():
        player = xbmc.Player()
        last_progress = 0
        update_interval = 30  # Update every 30 seconds
        
        while player.isPlaying():
            try:
                current_time = player.getTime()
                total_time = player.getTotalTime()
                
                if total_time > 0:
                    # Update progress if significant change
                    if current_time - last_progress > update_interval:
                        progress = int(current_time)
                        last_progress = current_time
                        
                        # Update watch progress
                        content_type = 'episode' if season else 'movie'
                        api.update_watch_progress(video_id, progress, content_type)
                        log(f"Progress updated: {progress}s / {total_time}s")
                
                # Check every 5 seconds
                xbmc.sleep(5000)
                
            except:
                break
        
        # Final progress update when playback ends
        try:
            if player.getTime():
                final_progress = int(player.getTime())
                content_type = 'episode' if season else 'movie'
                api.update_watch_progress(video_id, final_progress, content_type)
        except:
            pass
    
    # Start progress tracking thread
    thread = threading.Thread(target=progress_tracker)
    thread.daemon = True
    thread.start()

# ============ Search Functions ============

def search_content(api, params):
    """Search for content"""
    log(f"Search with params: {params}")
    
    query = params.get('query', '')
    content_type = params.get('content_type', '')
    
    if not query:
        # Show keyboard dialog with search history
        search_history = get_setting('search_history', '').split('|')
        if search_history:
            choices = ['New Search'] + search_history[:5]
            selected = xbmcgui.Dialog().select("Search Tubi TV", choices)
            if selected == 0:
                kb = xbmc.Keyboard('', 'Search Tubi TV')
                kb.doModal()
                if kb.isConfirmed():
                    query = kb.getText()
            elif selected > 0:
                query = choices[selected]
        else:
            kb = xbmc.Keyboard('', 'Search Tubi TV')
            kb.doModal()
            if kb.isConfirmed():
                query = kb.getText()
    
    if not query:
        return
    
    # Save search history
    save_search_history(query)
    
    # Add search type filter
    list_item = xbmcgui.ListItem(label=f"Search Results for: {query}")
    list_item.setArt({'icon': 'DefaultSearch.png'})
    xbmcplugin.addDirectoryItem(HANDLE, '', list_item, False)
    
    # Add type filters
    for type_name, type_value in [('All', ''), ('Movies', 'movie'), ('TV Shows', 'tvshow')]:
        list_item = xbmcgui.ListItem(label=f"  {type_name}")
        url = build_url({
            'mode': 'search_results',
            'query': query,
            'content_type': type_value
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)
    
    # Also show results directly
    show_search_results(api, query, content_type)

def search_suggestions(api, params):
    """Show search suggestions"""
    query = params.get('query', '')
    if not query:
        return
    
    suggestions = api.search_suggestions(query)
    
    for suggestion in suggestions:
        list_item = xbmcgui.ListItem(label=suggestion)
        url = build_url({
            'mode': 'search',
            'query': suggestion
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)

def show_search_results(api, query, content_type='', page=1):
    """Display search results"""
    log(f"Showing search results for: {query}, type: {content_type}")
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        results = api.search(query, page, content_type=content_type if content_type else None)
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not results:
            xbmcgui.Dialog().ok(ADDON_NAME, "No results found")
            return
        
        for item in results:
            list_item = xbmcgui.ListItem(label=item['title'])
            
            list_item.setArt({
                'thumb': item.get('thumbnail', ''),
                'poster': item.get('poster', item.get('thumbnail', '')),
                'fanart': item.get('fanart', item.get('background', ''))
            })
            
            info = {
                'title': item.get('title', ''),
                'plot': item.get('plot', item.get('description', '')),
                'year': item.get('year', ''),
                'rating': item.get('rating', 0),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            item_type = item.get('type', 'movie')
            if item_type == 'movie':
                url = build_url({
                    'mode': 'play',
                    'video_id': item['id'],
                    'title': item['title'],
                    'thumbnail': item.get('thumbnail', ''),
                    'description': item.get('plot', item.get('description', ''))
                })
                is_folder = False
            else:
                url = build_url({
                    'mode': 'list_seasons',
                    'show_id': item['id'],
                    'title': item['title'],
                    'thumbnail': item.get('thumbnail', '')
                })
                is_folder = True
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE,
                url=url,
                listitem=list_item,
                isFolder=is_folder
            )
        
        # Add pagination
        add_pagination('search_results', {'query': query, 'content_type': content_type}, page)
            
    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        log(f"Error searching: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, _(30007))

def save_search_history(query):
    """Save search query to history"""
    search_history = get_setting('search_history', '')
    history_list = search_history.split('|') if search_history else []
    
    # Remove if already exists
    if query in history_list:
        history_list.remove(query)
    
    # Add to front
    history_list.insert(0, query)
    
    # Keep last 10
    history_list = history_list[:10]
    
    set_setting('search_history', '|'.join(history_list))

# ============ User Account Functions ============

def login(api):
    """Handle user login"""
    log("Login requested")
    
    # Get credentials from user
    email = xbmcgui.Dialog().input(_(30008), type=xbmcgui.INPUT_ALPHANUM)
    if not email:
        return
    
    password = xbmcgui.Dialog().input(_(30009), type=xbmcgui.INPUT_ALPHANUM, 
                                      option=xbmcgui.ALPHANUM_HIDE_INPUT)
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
    
    if xbmcgui.Dialog().yesno(ADDON_NAME, _(30018)):
        api = TubiAPI()
        api.logout()
        set_setting('username', '')
        xbmcgui.Dialog().ok(ADDON_NAME, "Logged out successfully")
        # Refresh the menu
        xbmc.executebuiltin('Container.Refresh')

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
        
        if not items:
            xbmcgui.Dialog().ok(ADDON_NAME, "Your list is empty")
            return
        
        for item in items:
            list_item = xbmcgui.ListItem(label=item['title'])
            
            list_item.setArt({
                'thumb': item.get('thumbnail', ''),
                'poster': item.get('poster', item.get('thumbnail', '')),
                'fanart': item.get('fanart', item.get('background', ''))
            })
            
            info = {
                'title': item.get('title', ''),
                'plot': item.get('description', ''),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            # Add remove from list context menu
            context_menu = [(
                'Remove from My List',
                f'RunPlugin({build_url({"mode": "remove_from_list", "content_id": item["id"], "title": item["title"]})})'
            )]
            list_item.addContextMenuItems(context_menu)
            
            item_type = item.get('type', 'movie')
            if item_type == 'movie':
                url = build_url({
                    'mode': 'play',
                    'video_id': item['id'],
                    'title': item['title'],
                    'thumbnail': item.get('thumbnail', ''),
                    'description': item.get('description', '')
                })
                is_folder = False
            else:
                url = build_url({
                    'mode': 'list_seasons',
                    'show_id': item['id'],
                    'title': item['title'],
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

def add_to_list(api, params):
    """Add content to user's list"""
    if not api.is_authenticated():
        xbmcgui.Dialog().ok(ADDON_NAME, "Please login first")
        return
    
    content_id = params.get('content_id')
    content_type = params.get('content_type', 'movie')
    title = params.get('title', '')
    
    if not content_id:
        return
    
    success = api.add_to_my_list(content_id, content_type)
    
    if success:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Added '{title}' to your list")
    else:
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to add to list")

def remove_from_list(api, params):
    """Remove content from user's list"""
    if not api.is_authenticated():
        return
    
    content_id = params.get('content_id')
    title = params.get('title', '')
    
    if not content_id:
        return
    
    if xbmcgui.Dialog().yesno(ADDON_NAME, f"Remove '{title}' from your list?"):
        success = api.remove_from_my_list(content_id)
        
        if success:
            xbmcgui.Dialog().ok(ADDON_NAME, f"Removed '{title}' from your list")
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().ok(ADDON_NAME, "Failed to remove from list")

def watch_history(api):
    """Display user's watch history"""
    log("Accessing Watch History")
    
    if not api.is_authenticated():
        xbmcgui.Dialog().ok(ADDON_NAME, "Please login first to access watch history")
        return
    
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    
    try:
        history = api.get_watch_history()
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        
        if not history:
            xbmcgui.Dialog().ok(ADDON_NAME, "No watch history found")
            return
        
        for item in history[:50]:  # Limit to 50 items
            list_item = xbmcgui.ListItem(label=item['title'])
            
            list_item.setArt({
                'thumb': item.get('thumbnail', ''),
                'poster': item.get('poster', item.get('thumbnail', ''))
            })
            
            # Show progress
            progress = item.get('progress', 0)
            if progress > 0:
                list_item.setProperty('resume_time', str(progress))
                list_item.setProperty('total_time', str(item.get('duration', 0)))
            
            info = {
                'title': item.get('title', ''),
                'plot': item.get('description', ''),
                'studio': 'Tubi TV'
            }
            list_item.setInfo('video', info)
            
            item_type = item.get('type', 'movie')
            if item_type == 'movie':
                url = build_url({
                    'mode': 'play',
                    'video_id': item['id'],
                    'title': item['title'],
                    'thumbnail': item.get('thumbnail', ''),
                    'description': item.get('description', '')
                })
                is_folder = False
            else:
                url = build_url({
                    'mode': 'list_seasons',
                    'show_id': item['id'],
                    'title': item['title'],
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
        log(f"Error loading watch history: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Error loading watch history")

# ============ Utility Functions ============

def add_sort_options(mode, base_params):
    """Add sorting options to directory"""
    sort_options = [
        ('Popular', 'popular'),
        ('Recent', 'recent'),
        ('Rating', 'rating'),
        ('Title', 'title')
    ]
    
    for label, value in sort_options:
        list_item = xbmcgui.ListItem(label=f"[Sort] {label}")
        list_item.setArt({'icon': 'DefaultSort.png'})
        
        params = base_params.copy()
        params['mode'] = mode
        params['sort_by'] = value
        
        url = build_url(params)
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)

def add_pagination(mode, base_params, current_page):
    """Add pagination controls"""
    # Next page
    next_page = current_page + 1
    list_item = xbmcgui.ListItem(label=f"Next Page ► ({next_page})")
    list_item.setArt({'icon': 'DefaultFolder.png'})
    
    params = base_params.copy()
    params['mode'] = mode
    params['page'] = next_page
    
    url = build_url(params)
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)
    
    # Previous page if not on first
    if current_page > 1:
        prev_page = current_page - 1
        list_item = xbmcgui.ListItem(label=f"◄ Previous Page ({prev_page})")
        list_item.setArt({'icon': 'DefaultFolder.png'})
        
        params = base_params.copy()
        params['mode'] = mode
        params['page'] = prev_page
        
        url = build_url(params)
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, True)

def clear_cache_dialog():
    """Clear cache with confirmation"""
    if xbmcgui.Dialog().yesno(ADDON_NAME, "Clear all cached data?"):
        clear_cache()
        xbmcgui.Dialog().ok(ADDON_NAME, _(30020))
        xbmc.executebuiltin('Container.Refresh')

# ============ Entry Point ============

if __name__ == '__main__':
    param_string = sys.argv[2][1:] if len(sys.argv) > 2 else ''
    router(param_string)
