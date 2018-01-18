# -*- coding: utf-8 -*-
#!/usr/bin/python
'''
/*
 * Title : authentication class
 * 
 * Version : 
 * 
 * Last modified date : 2016-1-28
 * 
 * Description :
 *         For generation of authorization signature for access of Aspen Cloud Server API
 *         Format Http Header :  Authorization: access_id + colon + Signature
 *         Example of "Authorization":   Authorization: 00001929933:dsfdsjfjdsf343rjkhj45rhjr4jwh
 * 
 * Prerequisite :
 *         - Python 2.5  or above
 *
 *
 * How to use this class :
 * 1) Instantiate a class and passing the "user access id" and "user secret key"
 * 2) Call function, setParameter, to pass all required information for signature generation.
 * 3) If you want to generature a signature only, you can call function, generateSignature().
 * 4) If you want to get a formatted "Authorization" header (i.e. Authorization: access_id:signature, 
 *    you can call function, getAuthHeader().
 * 
 */
'''

import base64
import hmac
try:
    from hashlib import sha1 as sha 
except:
    import sha


PUT = "PUT"
DELETE = "DELETE"
GET = "GET"
POST = "POST"
class CURLClientAuth:
    def __init__(self,_id,key):
        self.user_access_id = _id
        self.user_secret_key = key
        
        self.http_action = ""
        self.current_datetime = ""
        self.api_name = ""
        self.arrAction = ["PUT", "DELETE", "GET", "POST"]
    
    def setParameter(self, HttpAction, CurrentDateTime, API_Name):
        """
        Assign requested data for signature generation.
         
        Caution : If you haven't data for such field, you should assign EMPTY string.
                      e.g. Server_id = ""
          
        Parameter :
                 1) HttpAction - The http action including PUT, DELETE or GET
                 2) CurrentDateTime - Current date time
                 3) API_Name - API name for your request e.g. server_list, soft_shutdown
                 4) Server_id - Unique server ID
        """
        self.http_action = HttpAction
        self.current_datetime = CurrentDateTime
        self.api_name = API_Name
    
    def generateSignature(self):
        """
        #
        # Generate the signature 
        # 
        # Parameter : no parameter is required but should call "setParameter" to assign related value.
        # 
        # Return Value :
        #         Return signature if success
        #         Return boolean type False if failure
        #
        """
        try:
            self.arrAction.index(self.http_action)
        except:
            return False
        
        if self.user_access_id=='' or self.user_secret_key=='':
            return False
    
        request_string = "<" + self.http_action + ">"
        request_string += "<"+ self.current_datetime + ">"
        request_string += "<" + self.user_access_id + ">"
        request_string += "<" + self.api_name + ">"
        
        
        #print request_string
        signature = base64.encodestring(hmac.new(self.user_secret_key, request_string, sha).hexdigest()).strip()
        #signature = base64_encode(hash_hmac('sha1', request_string, self.user_secret_key))
    
        return (signature=='' and False  or signature)
    
    def getAuthHeader(self) :
        '''#
        # Get the formatted header
        # i.e. Authorization: access_id:signature
        # 
        # Parameter : no parameter is required.
        # 
        # Return Value :
        #         Return the formatted http header if signature can be generated successfully.
        #         Return boolean type False if failure
        #
        '''
        signature = self.generateSignature()
        if signature==False:
            return False
        
        return "Authorization: " + self.user_access_id + ":" + signature