# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
"""

import os
import re

from frame.logger import Log


class FormData(object):
    
    def __init__(self, form_data):
        self.file_name = ''
        self.content_type = ''
        self.field_name = ''
        self.content = ''
        self.parse_file_content(form_data)

    def parse_filename(self, txt):
        """
        # form-data; name="file"; filename="\xe9\x83\xa8\xe7\xbd\xb2\xe9\xab\x98\xe5\x8f\xaf\xe7\x94\xa8\xe6\x80\xa7MySQL.docx"
        """
        arr = txt.split('; ')
        data = {}
        for item in arr:
            arr1 = item.split('=')
            if len(arr1) == 2:
                data[arr1[0]] = arr1[1].replace('"', '')
                
        if 'name' in data:
            self.field_name = data['name'].strip()
            
        if 'filename' in data:
            self.file_name = data['filename'].strip()
    
    def parse_file_content(self, form_data):
        m = re.search(r'^-{6}.+', form_data)
        if not m:
            self.content = form_data
            return
        
        txt = m.group(0)
        index = form_data.rfind(txt)
        if index > 0:
            content = form_data[len(txt)+1:index]
        else:
            content = form_data[len(txt)+1:]
        
        m = re.search(r'^Content-Disposition: (.+)\nContent-Type: (.+)\n', content)
        if not m:
            self.content = content
            return
        
        txt = m.group(0)
        self.content = content[len(txt):].strip()
        self.parse_filename(m.group(1))
        self.content_type = m.group(2).strip()
        
    def is_docker_file(self):       
        return self.content_type == 'application/octet-stream' and self.file_name.lower() =='dockerfile' and self.find_docker_keys()
    
    def find_docker_keys(self):
        if self.content.find('FROM') >= 0 or self.content.find('ADD') >= 0 \
            or self.content.find('RUN') >= 0 or self.content.find('CMD') >= 0:
            return True
        return False
    
    
    def save_tar_file(self, folder):
        if not self.file_name.endswith('.tar.gz'):
            Log(1, 'save_tar_file fail, as the file is not a tar file.')
            return False
        
        if not os.path.isdir(folder):
            os.makedirs(folder)
        
        fullpath = os.path.join(folder, self.file_name)
        with open(fullpath, 'wb') as fd:
            fd.write(self.content)
            
        return fullpath
            
        
        
        
    

        
        
    
    
    