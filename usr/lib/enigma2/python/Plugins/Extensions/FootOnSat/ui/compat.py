# Source code from (https://github.com/Taapat/enigma2-plugin-youtube/blob/master/src/compat.py)
from sys import version_info
from threading import Thread

PY3 = version_info[0] == 3

# Disable certificate verification on python 2.7.9
if version_info >= (2, 7, 9):
	import ssl
	ssl._create_default_https_context = ssl._create_unverified_context


if version_info[0] == 2:
	# Python 2
	compat_str, compat_basestring, compat_chr = (unicode, basestring, unichr)
	compat_integer_types = (int, long)
	compat_numeric_types = (int, float, long, complex)

	from re import compile
	from urllib import _hextochr

	from itertools import izip_longest as compat_zip_longest
	from urllib import urlencode as compat_urlencode
	from urllib import quote as compat_quote
	from urllib import urlretrieve as compat_urlretrieve
	from urllib2 import urlopen
	from urllib2 import Request as compat_Request
	from urllib2 import HTTPError as compat_HTTPError
	from urllib2 import URLError as compat_URLError
	from urlparse import urljoin as compat_urljoin
	from urlparse import urlparse as compat_urlparse
	from urlparse import urlunparse as compat_urlunparse
	from httplib import HTTPException as compat_HTTPException
	from cookielib import MozillaCookieJar as compat_MozillaCookieJar


	def _unquote_to_bytes(string):
		if not string:
			return b''
		if isinstance(string, unicode):
			string = string.encode('utf-8')
		bits = string.split(b'%')
		if len(bits) == 1:
			return string
		res = [bits[0]]
		for item in bits[1:]:
			try:
				res.append(_hextochr[item[:2]])
				res.append(item[2:])
			except KeyError:
				res.append(b'%')
				res.append(item)
		return b''.join(res)

	def _unquote(string):
		if '%' not in string:
			string.split
			return string
		bits = compile(r'([\x00-\x7f]+)').split(string)
		res = [bits[0]]
		for i in range(1, len(bits), 2):
			res.append(_unquote_to_bytes(bits[i]).decode('utf-8', 'replace'))
			res.append(bits[i + 1])
		return ''.join(res)

	def _parse_qsl(qs):
		pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
		r = []
		for name_value in pairs:
			if not name_value:
				continue
			nv = name_value.split('=', 1)
			if len(nv) == 2 and len(nv[1]):
				name = unicode(_unquote(nv[0].replace('+', ' ')))
				value = unicode(_unquote(nv[1].replace('+', ' ')))
				r.append((name, value))
		return r

	def compat_parse_qs(qs):
		"""
		Correct parse_qs implementation from cpython 3's stdlib.
		Python 2's version is apparently totally broken.
		"""
		parsed_result = {}
		pairs = _parse_qsl(qs)
		for name, value in pairs:
			if name in parsed_result:
				parsed_result[name].append(value)
			else:
				parsed_result[name] = [value]
		return parsed_result

else:
	# Python 3
	compat_str, compat_basestring, compat_chr = (str, (str, bytes), chr)
	compat_integer_types = (int, )
	compat_numeric_types = (int, float, complex)

	from itertools import zip_longest as compat_zip_longest
	from urllib.parse import urlencode as compat_urlencode
	from urllib.parse import quote as compat_quote
	from urllib.request import urlretrieve as compat_urlretrieve
	from urllib.request import urlopen
	from urllib.request import Request as compat_Request
	from urllib.error import HTTPError as compat_HTTPError
	from urllib.error import URLError as compat_URLError
	from urllib.parse import urljoin as compat_urljoin
	from urllib.parse import urlparse as compat_urlparse
	from urllib.parse import parse_qs as compat_parse_qs
	from urllib.parse import urlunparse as compat_urlunparse
	from http.client import HTTPException as compat_HTTPException
	from http.cookiejar import MozillaCookieJar as compat_MozillaCookieJar

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


try:
	from future_builtins import map as compat_map
except ImportError:
	try:
		from itertools import imap as compat_map
	except ImportError:
		compat_map = map


compat_int = compat_integer_types[-1]

SUBURI = '&suburi='


def compat_urlopen(url, timeout=5):
	"""
	Urlopen in thread to enforce a timeout on the function call.
	Timeout in urlopen only affects how long Python waits before
	an exception is raised if the server has not issued a response.
	It does not enforce a time limit on the entire function call.
	"""
	compat_urlopen.response = None
	compat_urlopen.error = None

	def open_url(url, timeout):
		try:
			compat_urlopen.response = urlopen(url, timeout=timeout)
		except Exception as e:
			compat_urlopen.error = e

	t = Thread(target=open_url, args=(url, timeout))
	t.setDaemon(True)
	t.start()
	t.join(timeout + 1)
	if compat_urlopen.error:
		raise compat_urlopen.error
	return compat_urlopen.response


def compat_parse_iso(s):
	"""Parse ISO 8601 datetime string to epoch seconds (UTC). Works in Py2 and Py3."""
	import re as _re
	import calendar as _cal
	if not s:
		return 0
	s = str(s).strip()
	m = _re.match(r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(?:(Z)|([+-])(\d{2}):?(\d{2}))?$', s)
	if not m:
		return 0
	try:
		year = int(m.group(1))
		month = int(m.group(2))
		day = int(m.group(3))
		hour = int(m.group(4))
		minute = int(m.group(5))
		sec = int(m.group(6)) if m.group(6) else 0
		offset_sec = 0
		if m.group(8) and m.group(9) and m.group(10):
			sign = 1 if m.group(8) == '+' else -1
			offset_sec = sign * (int(m.group(9)) * 3600 + int(m.group(10)) * 60)
		dt = datetime(year, month, day, hour, minute, sec)
		return _cal.timegm(dt.timetuple()) - offset_sec
	except Exception:
		return 0
