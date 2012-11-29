import requests
from requests.auth import OAuth1
from oauth_hook import OAuthHook
from urlparse import parse_qs
import json

__all__ = ['FitbitCredentials', 'FitbitAuth', 'FitbitApi']


class FitbitCredentials(object):
    def __init__(self, access_token=None, access_token_secret=None, consumer_key=None, consumer_secret=None):
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret


class FitbitAuth(object):
    URL = 'https://api.fitbit.com/oauth'

    def __init__(self, consumer_key, consumer_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

    def get_authorize_url(self):
        oauth_hook = OAuthHook(consumer_key=self.consumer_key, consumer_secret=self.consumer_secret)
        response = requests.post('%s/request_token' % self.URL, hooks={'pre_request': oauth_hook})
        qs = parse_qs(response.text)
        self.oauth_token = qs['oauth_token'][0]
        self.oauth_secret = qs['oauth_token_secret'][0]
        return "%s/authorize?oauth_token=%s" % (self.URL, self.oauth_token)

    def get_credentials(self, oauth_verifier):
        oauth_hook = OAuthHook(self.oauth_token, self.oauth_secret, self.consumer_key, self.consumer_secret)
        response = requests.post('%s/access_token' % self.URL, {'oauth_verifier': oauth_verifier}, 
                                 hooks={'pre_request': oauth_hook})
        response = parse_qs(response.content)
        return FitbitCredentials(response['oauth_token'][0], response['oauth_token_secret'][0], 
                              self.consumer_key, self.consumer_secret)


class FitbitApi(object):
    URL = 'http://api.fitbit.com/1'

    def __init__(self, credentials):
        self.credentials = credentials
        self.oauth = OAuth1(unicode(credentials.consumer_key), unicode(credentials.consumer_secret),
                    unicode(credentials.access_token), unicode(credentials.access_token_secret),
                    signature_type='auth_header')
        self.client = requests.session(auth=self.oauth)

    def request(self, method, action, **kwargs):
        r = self.client.request(method, '%s%s.json' % (self.URL, action), **kwargs)
        r.raise_for_status()
        return json.loads(r.text)

    def get(self, action, **kwargs):
        return self.request('GET', action, params=kwargs)

    def post(self, action, data):
        return self.request('POST', action, data=data)
