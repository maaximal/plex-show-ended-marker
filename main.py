from plexapi.server import PlexServer
from plexapi.library import ShowSection
from plexapi.video import Show
from tmdbv3api import TMDb, TV, Search
from PIL import Image, ImageDraw
import os, sys, re, urllib.request, logging

def showInfo(show: Show):
    search = Search()
    tv = TV()
    title = show.title
    title_year_re = re.compile(r'(?P<name>([a-zA-Z ]*)) \((?P<year>\d\d\d\d)\)').match(show.title)
    if title_year_re is not None:
        title = title_year_re.group('name')
    tmdb_shows = search.tv_shows(term=str(title),release_year=show.year)
    if tmdb_shows.total_results == 0:
        tmdb_shows = search.tv_shows(term=str(title))
    if tmdb_shows.total_results > 0:
        status = tv.details(tmdb_shows[0].id).status
        if status == "Ended" or status == "Canceled":
            return {"id": tmdb_shows[0].id, "ended": True}
        else:
            return {"id": tmdb_shows[0].id, "ended": False}
    else:
        logging.warning("Could not find TMDB match for "+str(show.title))
        return {"id": None, "ended": False}
    
def adaptImage(poster_file_original, poster_file_adapted):
    source_img = Image.open(poster_file_original).convert("RGBA")
    draw = ImageDraw.Draw(source_img)
    triangle_size = source_img.width/100*ended_triangle_width_percentage
    draw.polygon([(0,0), (0, triangle_size), (triangle_size,0)], fill = ended_color)
    source_img.save(poster_file_adapted, "PNG")

exclude = []
ended_color = "#F05050"
ended_triangle_width_percentage = 13
if len(sys.argv) > 3:
    base_url = sys.argv[1]
    plex_token = sys.argv[2]
    tmdb_key = sys.argv[3]
    if len(sys.argv) > 4:
        exclude = sys.argv[4:]
else:
    base_url = os.environ.get('PLEX_BASEURL')
    plex_token = os.environ.get('PLEX_TOKEN')
    tmdb_key = os.environ.get('TVDB_API_KEY')
    exclude = os.environ.get('PLEX_EXCLUDE')
if base_url is None or plex_token is None or tmdb_key is None:
    logging.error("Missing baseurl and/or token and/or tvdb api key")
    exit()
plex = PlexServer(base_url, plex_token)
for section in plex.library.sections():
    if type(section) == ShowSection and section.title not in exclude:
        for show in section.all():
            if type(show) == Show:
                tmdb = TMDb()
                tmdb.api_key = tmdb_key
                info = showInfo(show)
                id = info["id"]
                poster_file_original = "./posters/"+str(id)+".png"
                poster_file_adapted = "./posters/"+str(id)+"_adapted.png"
                if info["ended"]:
                    if os.path.isfile(poster_file_adapted):
                        logging.info("Already adapted "+str(show.title))
                    else:
                        urllib.request.urlretrieve(show.posterUrl, poster_file_original)
                        adaptImage(poster_file_original, poster_file_adapted)
                        poster = show.uploadPoster(filepath=poster_file_adapted)
                        logging.info(show.title+" has ended")
                elif id is not None and not info["ended"] and os.path.isfile(poster_file_adapted): #series has returned from ended
                    poster = show.uploadPoster(filepath=poster_file_original)
                    os.remove(poster_file_adapted)
                    logging.info(show.title+" has returned")
