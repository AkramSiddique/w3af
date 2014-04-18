# -*- coding: UTF-8 -*-
"""
baseparser.py

Copyright 2006 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import re
import urllib

from w3af.core.data.constants.encodings import UTF8
from w3af.core.data.parsers.url import URL
from w3af.core.data.misc.encoding import is_known_encoding


class BaseParser(object):
    """
    This class is an abstract document parser.

    :author: Andres Riancho (andres.riancho@gmail.com)
    """
    SAFE_CHARS = (('\x00', '%00'),)

    #URL_RE = ('((http|https):[A-Za-z0-9/](([A-Za-z0-9$_.+!*(),;/?:@&~=-])|%'
    #    '[A-Fa-f0-9]{2})+(#([a-zA-Z0-9][a-zA-Z0-9$_.+!*(),;/?:@&~=%-]*))?)')
    URL_RE = re.compile('((http|https)://([\w:@\-\./]*?)[^ \n\r\t"\'<>]*)', re.U)

    def __init__(self, http_response):

        encoding = http_response.get_charset()
        if not is_known_encoding(encoding):
            raise ValueError('Unknown encoding: %s' % encoding)

        # "set_base_url"
        url = http_response.get_url()
        redir_url = http_response.get_redir_url()
        if redir_url:
            url = redir_url

        self._base_url = url
        self._baseDomain = url.get_domain()
        self._rootDomain = url.get_root_domain()
        self._encoding = http_response.get_charset()

        # To store results
        self._re_urls = set()

    def _regex_url_parse(self, doc_str):
        """
        Use regular expressions to find new URLs.

        :param HTTPResponse: The http response object that stores the
                             response body and the URL.
        :return: None. The findings are stored in self._re_urls as url_objects
        """
        re_urls = self._re_urls

        for url in self.URL_RE.findall(doc_str):
            # This try is here because the _decode_url method raises an
            # exception whenever it fails to decode a url.
            try:
                decoded_url = URL(self._decode_url(url[0]),
                                  encoding=self._encoding)
            except ValueError:
                pass
            else:
                re_urls.add(decoded_url)

        # Finally, normalize the urls
        map(lambda u: u.normalize_url(), re_urls)

    def _decode_url(self, url_string):
        """
        Decode `url_string` using urllib's url-unquote
        algorithm. The returned value is always a unicode string.

        See http://www.blooberry.com/indexdot/html/topics/urlencoding.htm for
        more info on urlencoding.

        So, when _decode_url() is called and take as input
        u'http://host.tld/%05%44', it is encoded using the instance's _encoding
        then it is applied the unquote routine and finally is decoded back to
        unicode being u'http://host.tld/é' the final result.

        Something small to remember:
        >>> urllib.unquote('ind%c3%a9x.html').decode('utf-8').encode('utf-8') \
        == 'ind\xc3\xa9x.html'
        True

        """
        enc = self._encoding

        if isinstance(url_string, unicode):
            url_string = url_string.encode(enc)

        dec_url = urllib.unquote(url_string)
        for sch, repl in self.SAFE_CHARS:
            dec_url = dec_url.replace(sch, repl)

        # Always return unicode
        # TODO: Any improvement for this? We're certainly losing
        # information by using the 'ignore' error handling

        try:
            dec_url = dec_url.decode(UTF8)
        except UnicodeDecodeError:
            dec_url = dec_url.decode(enc, 'ignore')
        #
        # TODO: Lines below will remain commented until we make a
        # decision regarding which is the (right?) way to decode URLs.
        # The tests made on FF and Chrome revealed that if strange
        # (i.e. non ASCII) characters are present in a URL the browser
        # will urlencode the URL string encoded until the beginning
        # of the query string using the page charset and the query
        # string itself encoded in UTF-8.
        #
        # Apparently this is not a universal practice. We've found
        # some static sites having URL's encoded *only* in Windows-1255
        # (hebrew) for example.
        #
        # This is what de W3C recommends (not a universal practice though):
        #    http://www.w3.org/TR/REC-html40/appendix/notes.html#h-B.2
        #
##        index = dec_url.find('?')
##        if index > -1:
##            dec_url = (dec_url[:index].decode(enc, 'ignore') +
##                       dec_url[index:].decode('utf-8', 'ignore'))

        return dec_url

    def get_forms(self):
        """
        :return: A list of forms.
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_forms() method.')

    def get_references(self):
        """
        Searches for references on a page. w3af searches references in every
        html tag, including:
            - a
            - forms
            - images
            - frames
            - etc.

        :return: Two sets, one with the parsed URLs, and one with the URLs that
                 came out of a regular expression. The second list if less
                 trustworthy.
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_references() method.')

    def get_emails(self, domain=None):
        """
        :return: A set with email addresses
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_emails() method.')

    def get_comments(self):
        """
        :return: A list of comments.
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_comments() method.')

    def get_scripts(self):
        """
        :return: A list of scripts (like javascript).
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_scripts() method.')

    def get_meta_redir(self):
        """
        :return: Returns list of meta redirections.
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_meta_redir() method.')

    def get_meta_tags(self):
        """
        :return: Returns list of all meta tags.
        """
        raise NotImplementedError('You should create your own parser class '
                                  'and implement the get_meta_tags() method.')

    def _return_empty_list(self, *args, **kwds):
        """
        Some parsers don't implement some of the features, so they can add
        something like:

        get_forms = _return_empty_list

        At the class definition, and simply return an empty list.
        """
        return []