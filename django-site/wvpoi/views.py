from django.shortcuts import render
from django.http import HttpResponse
import os
import re
import json
from . import settings
from . import utils
from . import languages
from . import models


class WikivoyageListingsFile(object):
    def __init__(self, name, language, date, file_format, is_compressed):
        self._name = name
        self._language = language
        self._date = date
        self._file_format = file_format
        self._is_compressed = is_compressed

    @staticmethod
    def parse(filename):
        m = re.match('^wikivoyage-listings-(\S{2})-([^.]+).(.*?)(.bz2|)$', filename)
        if not m:
            return None
        else:
            return WikivoyageListingsFile(
                filename, m.group(1), m.group(2), m.group(3), m.group(4) == '.bz2'
            )

    @property
    def language_code(self):
        return self._language

    @property
    def language_title(self):
        return {
            'en': 'English',
            'ru': 'Russian',
            'fr': 'French'
        }.get(self.language_code, 'Unknown')

    @property
    def date_title(self):
        if self.is_latest:
            return 'Latest'
        else:
            return self._date

    @property
    def file_format(self):
        return self._file_format

    @property
    def file_format_title(self):
        return {
            'csv': 'CSV',
            'kml': 'KML',
            'gpx': 'GPX',
            'sql': 'SQL',
            'osmand.gpx': 'GPX for OsmAnd',
            'obf': 'OBF (for OsmAnd), "wikivoyage" POI type',
            'user-defined.obf': 'OBF (for OsmAnd), "user-defined" POI type',
            'xml': 'XML, "wikivoyage" POI type',
            'user-defined.xml': 'XML, "user-defined" POI type',
            'validation-report.html': 'Validation report (HTML)'
        }.get(self._file_format, self._file_format)

    @property
    def compressed_title(self):
        return 'Yes' if self._is_compressed else 'No'

    @property
    def filename(self):
        return self._name

    @property
    def is_latest(self):
        return self._date == 'latest'

    @property
    def size_title(self):
        size = os.path.getsize(os.path.join(settings.LISTINGS_DIR, self._name))
        return utils.format_file_size(size)
    

def filter_none_values(lst):
    return [i for i in lst if i is not None]


def index(request):
    all_listings = filter_none_values(
        WikivoyageListingsFile.parse(filename) 
        for filename in os.listdir(settings.LISTINGS_DIR)
    )
    latest_listings = [l for l in all_listings if l.is_latest]
    latest_listings = sorted(latest_listings, key=lambda l: (l.language_code, l.file_format))
    context = {
        'latest_listings': latest_listings,
        'languages': languages.Languages.get_all_languages()
    }
    return render(request, 'wvpoi/index.html', context)


def listings(request):
    all_listings = filter_none_values(
        WikivoyageListingsFile.parse(filename) 
        for filename in os.listdir(settings.LISTINGS_DIR)
    )
    all_listings = sorted(all_listings, key=lambda l: (l.date_title, l.language_code, l.file_format))
    context = {
        'all_listings': all_listings,
        'languages': languages.Languages.get_all_languages()
    }
    return render(request, 'wvpoi/listings.html', context)


def tool(request):
    context = {
        'languages': languages.Languages.get_all_languages()
    }
    return render(request, 'wvpoi/tool.html', context)

def get_listings(request):
    result = []

    filter_language = request.GET.get('language', '')
    filter_dict = {}
    exclude_dict = {}

    if filter_language:
        filter_dict['language'] = filter_language

    filter_article = request.GET.get('article', '')
    if filter_article:
        filter_dict['article'] = filter_article

    positional_data = request.GET.get('positional_data', '')
    if positional_data == 'true':
        exclude_dict['latitude__isnull'] = True
        exclude_dict['longitude__isnull'] = True

    output_format = request.GET.get('format', 'json')

    for listing in models.Listing.objects.filter(**filter_dict).exclude(**exclude_dict)[:500]:
        if output_format == 'geojson':
            result.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(listing.longitude), float(listing.latitude)]
                },
                "properties": {
                    "name": listing.title
                }
            })
        else:
            result.append({
                'title': listing.title,
                'language': listing.language,
                'article': listing.article,
                'type': listing.type,
                'latitude': str(listing.latitude),
                'longitude': str(listing.longitude)
            })

    return HttpResponse(json.dumps(result))
