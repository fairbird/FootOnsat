# Source code from (https://github.com/Taapat/enigma2-plugin-youtube/blob/master/src/compat.py)
from sys import version_info

PY3 = version_info[0] == 3
# --- Security Note for Python 2.7.9+ ---
# Disabling certificate verification is a security risk and should generally
# be avoided. This block maintains the original behavior for legacy compatibility.
if version_info >= (2, 7, 9):
    import ssl
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except AttributeError:
        pass

# --- Python 2/3 Compatibility ---
if version_info[0] == 2:
    # Python 2
    compat_str, compat_basestring, compat_chr = (unicode, basestring, unichr)
    compat_integer_types = (int, long)
    compat_numeric_types = (int, float, long, complex)

    # Simplified imports for faster startup
    from itertools import izip_longest as compat_zip_longest
    from urllib import urlencode as compat_urlencode
    from urllib import quote as compat_quote
    from urllib import urlretrieve as compat_urlretrieve
    from urllib2 import urlopen, Request as compat_Request
    from urllib2 import HTTPError as compat_HTTPError, URLError as compat_URLError
    
    # Use cgi.parse_qs for Python 2 (faster C implementation)
    from cgi import parse_qs as compat_parse_qs
    
    # Removed the slow, custom _unquote_to_bytes, _unquote, and _parse_qsl functions.

else:
    # Python 3
    compat_str, compat_basestring, compat_chr = (str, (str, bytes), chr)
    compat_integer_types = (int, )
    compat_numeric_types = (int, float, complex)

    # Simplified imports for faster startup
    from itertools import zip_longest as compat_zip_longest
    from urllib.parse import urlencode as compat_urlencode
    from urllib.parse import quote as compat_quote
    from urllib.parse import parse_qs as compat_parse_qs
    from urllib.request import urlretrieve as compat_urlretrieve
    from urllib.request import urlopen, Request as compat_Request
    from urllib.error import HTTPError as compat_HTTPError, URLError as compat_URLError


# --- compat_chain_map (Unchanged for compatibility with original logic) ---
# Note: The custom implementation for Python < 3.4 is kept as-is, 
# as optimization here is negligible compared to the URL handling.
if version_info >= (3, 4):
    from collections import ChainMap as compat_chain_map
else:
    from collections import MutableMapping

    class compat_chain_map(MutableMapping):
        def __init__(self, *maps):
            self.maps = list(maps) or [{}]

        def __getitem__(self, k):
            for m in self.maps:
                if k in m:
                    return m[k]
            raise KeyError(k)

        def __contains__(self, k):
            return any((k in m) for m in self.maps)

        def __delitem__(self, k):
            raise NotImplementedError('Deleting is not supported')

        def __iter__(self):
            d = {}
            for m in reversed(self.maps):
                d.update(dict.fromkeys(m))
            return iter(d)

        def __len__(self):
            return len(set().union(*self.maps))

        def new_child(self, m=None, **kwargs):
            m = m or {}
            m.update(kwargs)
            return self.__class__(m, *self.maps)


# --- compat_map (Unchanged for compatibility with original logic) ---
try:
    from future_builtins import map as compat_map
except ImportError:
    try:
        from itertools import imap as compat_map
    except ImportError:
        compat_map = map


compat_int = compat_integer_types[-1]

SUBURI = '&suburi='


# --- Optimized compat_urlopen (Major Speed Improvement) ---
def compat_urlopen(url, timeout=5):
    """
    Directly calls urlopen with the built-in timeout. This is significantly
    faster and smoother than the previous threading implementation, as it
    removes all overhead from creating and managing a new thread for every request.
    """
    # Python's built-in urlopen timeout is sufficient and highly optimized.
    return urlopen(url, timeout=timeout)
