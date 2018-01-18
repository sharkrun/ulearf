# -*- coding: utf-8 -*-
# !/usr/bin/python25


import cStringIO
import json
import time

import pycurl

from frame.exception import InternalException
from frame.logger import Log, PrintStack


# Http constants
PUT = "PUT"
GET = "GET"
DELETE = "DELETE"
POST = "POST"
HEAD = "HEAD"

# Http status code
HTTP_EXCEPTION = 1
HTTP_OK_200 = 200  # OK
HTTP_CREATED_201 = 201  # resource created
HTTP_ACCEPTED_202 = 202
HTTP_UNAUTHORIZED = 401  # authentication required
# Http header constants
HEADER_HOST = 'Host'
HEADER_DATE = 'Date'
HEADER_AUTH = 'Authorization'
HEADER_EXPIRES = 'Expires'
HEADER_ADMIN = 'x-pan-admin'

SUCCESS = "SUCCESS"
FAIL = "FAILURE"


class Response(object):
    def __init__(self, respond_body, respond_headers, status_code=HTTP_OK_200, msg="done"):
        """
        respond_http_status_code = ch.getinfo( pycurl.HTTP_CODE )
            respond_headers_array = ch.respondheader.getvalue()
            respond_body = ch.response.getvalue()
        """
        super(Response, self).__init__()
        self.status_code = status_code
        self.respond_headers = respond_headers
        self.respond_body = respond_body.decode('utf8')
        self.message = msg

    @property
    def success(self):
        return self.status_code == HTTP_OK_200

    @property
    def fail(self):
        return self.status_code < 200 or self.status_code > 299

    def __getitem__(self, key):
        if "body" == key:
            return self.respond_body
        elif "status_code" == key:
            return getattr(self, "status_code", 0)
        elif "message" == key:
            return self.message
        else:
            return None

    def __str__(self):
        return "Response<'status_code':%d,'headers':'%s','body':%s,'message':'%s'>" % \
               (self.status_code, self.respond_headers, self.respond_body, self.message)

    def log(self, act):
        if self.status_code == HTTP_OK_200:
            Log(4, '[%s] success, return [%s]' % (act, self.respond_body))
        else:
            Log(1, '[%s] fail, return [%s],massage[%s]' % (act, self.respond_body, self.message))

    def json_data(self):
        try:
            return json.loads(self.respond_body)
        except Exception:
            PrintStack()
            Log(1, "parse_2_json[%s]fail" % (self.respond_body))

        return None


class CURLClient(object):
    def __init__(self, domain='127.0.0.1'):
        self.domain = domain
        self.debug = False
        self.url = ""

        self.respond_headers_array = []

    def do_get(self, url, token=None, **args):
        return self.callRemote(str(url), GET, token, **args)

    def do_head(self, url, token=None, **args):
        return self.callRemote(url, HEAD, token, **args)

    def do_delete(self, url, token=None, **args):
        return self.callRemote(url, DELETE, token, **args)

    def do_put(self, url, data, token=None, **args):
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.callRemote(url, PUT, token, data, **args)

    def do_post(self, url, data='', token=None, **args):
        if isinstance(data, dict):
            data = json.dumps(data)

        return self.callRemote(url, POST, token, data, **args)

    def callRemote(self, url, method, token=None, post_data=None, **args):
        try:
            Headers = self.getBasicHeaders(token, **args)
            response = self.send_http_request(url, Headers, method, post_data)
            Log(4, u"callRemote[%s][%s]return[%s]"% (method, url, response.respond_body))
        except InternalException,e:
            Log(1, 'call_remote InternalException[%s][%s]except[%s]'%(method, url, e.value))
            return Response('', '', HTTP_EXCEPTION, str(e))
        except Exception, e:
            Log(4, u"callRemote Exception[%s][%s]except[%s]"% (method, url, str(e)))
            return Response('', '', HTTP_EXCEPTION, str(e))
        else:
            return response

    def send_http_request(self, thisURL, thisArrHeader, thisHttpMethod, thisHttpBody=""):
        try:
            ch = ""
            ch = pycurl.Curl()
            ch.setopt(pycurl.URL, str(thisURL))
            ch.setopt(pycurl.HTTPHEADER, thisArrHeader)
            ch.respondheader = cStringIO.StringIO()
            ch.setopt(pycurl.HEADERFUNCTION, ch.respondheader.write)
            ch.setopt(pycurl.CONNECTTIMEOUT, 30)
            ch.setopt(pycurl.TIMEOUT, 30)
            ch.setopt(pycurl.NOSIGNAL, 1)

            # ch.setopt( pycurl.VERBOSE, self.debug )

            #            c.setopt(pycurl.UPLOAD,1)
            #            try:
            #                c.setopt(pycurl.READFUNCTION, open(self.file_path, 'rb').read)
            #                filesize = os.path.getsize(self.file_path)
            #                c.setopt(pycurl.INFILESIZE, filesize)
            #
            #                c.response = cStringIO.StringIO()
            #                c.setopt(c.WRITEFUNCTION, c.response.write)
            #            except:
            #                c.close()
            #                raise CBSError("Open file <"+self.file_path+"> error!")

            if (thisHttpMethod == PUT or thisHttpMethod == POST) and thisHttpBody != "":
                handle = cStringIO.StringIO()
                handle.write(thisHttpBody)
                handle.seek(0)
                size = len(thisHttpBody)
                ch.setopt(pycurl.UPLOAD, True);
                ch.setopt(pycurl.READFUNCTION, handle.read);
                ch.setopt(pycurl.INFILESIZE, size);
            ch.setopt(pycurl.CUSTOMREQUEST, thisHttpMethod)

            if thisHttpMethod == HEAD:
                # ch.setopt( pycurl.HEADER, True )
                ch.setopt(pycurl.NOBODY, True)
            else:
                ch.response = cStringIO.StringIO()
                ch.setopt(ch.WRITEFUNCTION, ch.response.write)

            ch.perform()
            respond_http_status_code = ch.getinfo(pycurl.HTTP_CODE)
            respond_headers_array = ch.respondheader.getvalue()
            if thisHttpMethod == HEAD:
                respond_body = respond_headers_array
            else:
                respond_body = ch.response.getvalue()

            return Response(respond_body, respond_headers_array, respond_http_status_code)
        except pycurl.error, e:
            raise InternalException(e[1], e[0])
        except Exception, e:
            PrintStack()
            return Response('', '', HTTP_EXCEPTION, str(e))
        finally:
            if ch != '':
                ch.close()

    def getBasicHeaders(self, token=None, **args):
        '''
        return the basic required headers
        '''
        if 'Header' in args:
            Header = args['Header']
        else:
            Header = []

        # Header.append( 'Content-Type: application/json' )
        Header.append(HEADER_HOST + ": " + self.domain)
        Header.append(HEADER_DATE + ": " + time.strftime("%a, %d %b %Y %X +0000", time.gmtime()))

        if token:
            Header.append(HEADER_AUTH + ": Bearer %s" % (token))
        return Header
    