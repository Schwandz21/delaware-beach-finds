"""Lewes Historical Society — The Events Calendar REST API.

A verified nonprofit institution (precedence: nonprofit, below municipal). It is
the strongest structured Lewes calendar available: the City of Lewes site
publishes no feed, and this one carries exactly the maritime and history
programming the publication covers.
"""
from .tribe import fetch_tribe

NAME = 'Lewes Historical Society'
HOME = 'https://www.historiclewes.org/events/'
API = 'https://www.historiclewes.org/wp-json/tribe/events/v1/events'


def fetch(**kw):
    return fetch_tribe(name=NAME, home=HOME, api=API, source_type='nonprofit',
                       first_party=True, default_town='Lewes',
                       id_prefix='lewes', **kw)
