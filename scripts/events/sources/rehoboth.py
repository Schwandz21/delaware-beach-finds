"""City of Rehoboth Beach — The Events Calendar REST API.

First-party municipal source. https://www.rehobothbeachde.gov/events/
"""
from .tribe import fetch_tribe

NAME = 'City of Rehoboth Beach'
HOME = 'https://www.rehobothbeachde.gov/events/'
API = 'https://www.rehobothbeachde.gov/wp-json/tribe/events/v1/events'


def fetch(**kw):
    return fetch_tribe(name=NAME, home=HOME, api=API, source_type='municipal',
                       first_party=True, default_town='Rehoboth Beach',
                       id_prefix='rehoboth', **kw)
