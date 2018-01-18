# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.

from common.util import Result
from console.zonemgr import ZoneMgr
from frame.Logger import Log
from frame.errcode import FAIL, SUCCESS
from frame.ipcalc import Network
from frame.sysconfig import MACStr, IPStr
from mongodb.dbconst import ID
from mongoimpl.ipinfoimpl import IPInfoDBImpl
from mongoimpl.subnetimpl import SubNetDBImpl


class Subnet(Network):
    def __init__(self, subnet_id, ip, netmask=None, gateway=None):
        super(Subnet, self).__init__(ip, netmask)
        self.subnet_id = subnet_id

        if gateway == None:
            self.gateway = self.host_first().dq
        else:
            self.gateway = gateway

        self.ip_segment = self.network().dq
        self.netmask = self.netmask().dq

    def load_data(self):
        self.__ip_list = []
        rlt = IPInfoDBImpl.instance().read_record_list({"subnet_id": self.subnet_id}, fields=["ip_number"])
        if not rlt.success:
            Log(2, "IPInfoDBImpl.load data fail,as[%s]" % (rlt.message))
            return FAIL

        for ip_info in rlt.content:
            self.__ip_list.append(ip_info.get("ip_number"))

        return SUCCESS

    def get_lan_ip(self, mac):
        """
        """
        rlt = IPInfoDBImpl.instance().read_record_data({"mac": mac})
        if not rlt.success:
            Log(4, "Subnet.get_lan_ip don't find ip info by mac, mac = %s" % mac)
            return Result("", FAIL, "Subnet.get_lan_ip don't find ip info by mac")

        IPinfo = rlt.content
        return Result(IPinfo)

    def get_all_ip(self):
        rlt = IPInfoDBImpl.instance().read_record_list({"subnet_id": self.subnet_id})
        if not rlt.success:
            Log(4, "Subnet.get_all_ip don't find ip info")

        return rlt

    def request_ip(self, mac=None):
        """
        """
        res = self.load_data()
        if res == FAIL:
            Log(2, "Subnet.request_ip load data fail. subnet_id = %s" % self.subnet_id)
            return Result("", FAIL, "Subnet.request_ip load data fail.")

        # 在当前子网给MAC分配IP之前，删除在其他子网绑定的记录
        if mac != None:
            rlt = self.get_lan_ip(mac)
            if rlt.success:
                Log(3, "Subnet.request_ip mac address already has ip, so release first.")
                self.release_ip(mac)

        # 第一个IP地址用作网关
        has = False
        for ip_index in range(2, self.size()):
            if ip_index not in self.__ip_list:
                has = True
                break

        if has == False:
            Log(2, "Subnet.request_ip Subnet hasn't enough ip.")
            return Result("", FAIL, "Subnet.request_ip Subnet hasn't enough ip.")

        ip = self.host_index(ip_index).dq

        ipinfo = {}
        ipinfo["hostname"] = ip.replace(".", "_")
        ipinfo["subnet_id"] = self.subnet_id
        ipinfo["ip"] = ip
        ipinfo["netmask"] = self.netmask
        ipinfo["ip_number"] = ip_index
        ipinfo["routers"] = self.gateway
        ipinfo["mac"] = mac

        rlt = IPInfoDBImpl.instance().create_ip_record(ipinfo)
        if not rlt.success:
            Log(2, "Subnet.request_ip save to db fail,as[%s]" % (rlt.message))
            return Result("", FAIL, "Subnet.request_ip save to db fail")
        ipinfo["_id"] = rlt.content
        return Result(ipinfo)

    def release_ip(self, info):
        '''
        #回收指定mac or private_ip地址的ip资源;
        '''
        m = MACStr()
        p = IPStr()
        if not m.is_invalid(info):
            mac = info
            rlt = self.get_lan_ip(mac)
            if not rlt.success:
                Log(2, "Subnet.release_ip don't find ip info by mac, mac = %s" % mac)
                return Result(SUCCESS)

            IPinfo = rlt.content
            # IPinfo_list = rlt.content
            # if len(IPinfo_list) != 1:
            #    Log(2, "Subnet.release_ip find in info by mac not only one, all recoed = %s"%IPinfo_list)

            IPInfoDBImpl.instance().remove({"mac": IPinfo["mac"]})
        elif not p.is_invalid(info):
            private_ip = info
            IPInfoDBImpl.instance().remove({"ip": private_ip})
        else:
            Log(2, "Subnet.release_ip para error, info = %s" % info)
            return Result("", FAIL, "Subnet.release_ip para error!")

        return Result(SUCCESS)

    def request_multi_ip(self, num=1):
        """
        """
        res = self.load_data()
        if res == FAIL:
            Log(2, "Subnet.request_ip load data fail. subnet_id = %s" % self.subnet_id)
            return Result("", FAIL, "Subnet.request_ip load data fail.")

        index_list = []
        has = False
        for ip_index in range(2, self.size()):
            if ip_index not in self.__ip_list:
                index_list.append(ip_index)
                if len(index_list) >= num:
                    has = True
                    break

        if has == False:
            Log(2, "Subnet.request_ip Subnet hasn't enough ip.")
            return Result("", FAIL, "Subnet.request_ip Subnet hasn't enough ip.")

        ip_list = []
        for ip_index in index_list:
            ip = self.host_index(ip_index).dq

            ipinfo = {}
            # ipinfo["hostname"] = ip.replace(".", "_")
            ipinfo["subnet_id"] = self.subnet_id
            ipinfo["ip"] = ip
            ipinfo["netmask"] = self.netmask
            ipinfo["ip_number"] = ip_index
            ipinfo["routers"] = self.gateway
            # ipinfo["mac"] = None

            rlt = IPInfoDBImpl.instance().create_ip_record(ipinfo)
            if not rlt.success:
                Log(2, "Subnet.request_ip save to db fail,as[%s]" % (rlt.message))
                return Result("", FAIL, "Subnet.request_ip save to db fail")
            ipinfo["_id"] = rlt.content
            ip_list.append(ipinfo)

        return Result(ip_list)

    def release_multi_ip(self, ip_list):
        '''
        #回收ip资源;
        '''
        p = IPStr()
        for ip in ip_list:
            if not p.is_invalid(ip):
                Log(2, "Subnet.release_ip para error, ip = %s" % ip)
                return Result("", FAIL, "Subnet.release_ip para error!")

        for private_ip in ip_list:
            IPInfoDBImpl.instance().remove({"ip": private_ip})

        return Result(SUCCESS)

    def release(self):
        '''
        #释放所有分配出去的ip资源 ;
        '''
        IPInfoDBImpl.instance().remove({"subnet_id": self.subnet_id})
        return Result(SUCCESS)


class SubnetMgr(Network):
    def __init__(self, zone_id=None):
        self.zone_id = zone_id

        privte_start_ip = ZoneMgr.instance().get_subnet(self.zone_id)
        super(SubnetMgr, self).__init__(privte_start_ip, None)

        subnet_mask_length = ZoneMgr.instance().get_subnet_mask_length(self.zone_id)
        if subnet_mask_length < 8 or subnet_mask_length > 31:
            raise Exception("subnet mask length [%s] error, 8 < length < 31" % (subnet_mask_length))

            # self.privte_start_ip = self.host_first().dq
        self.sub_net_num = 4096
        self.subnet_mask_lenth = subnet_mask_length
        self.dbmgr = SubNetDBImpl.instance()

    def load_data(self):
        self.__index_store = []
        rlt = self.dbmgr.read_record_list()
        if not rlt.success:
            Log(2, "SubNetMgr.load data fail,as[%s]" % (rlt.message))
            return FAIL

        for record in rlt.content:
            self.__index_store.append(record["subnet_number"])

        return SUCCESS

    def get_subnet_by_vlan_id(self, vlan_id):
        rlt = self.dbmgr.read_record_data({"zone_id": self.zone_id, "vlan_id": vlan_id})
        if not rlt.success:
            Log(2, "SubNetMgr.get_subnet_by_vlan_id fail.")
            return Result("", FAIL, "SubNetMgr.get_subnet_by_vlan_id fail.")

        info = rlt.content
        subnet = Subnet(info[ID], info["ip"], info["netmask_length"], info["router"])
        return Result(subnet)

    def get_subnet_gateway_by_vlan_id(self, vlan_id):
        rlt = self.get_subnet_by_vlan_id(vlan_id)
        if not rlt.success:
            Log(2, "SubnetMgr.get_subnet_gateway_by_vlan_id fail.")
            return (None, None)

        subnet = rlt.content
        gateway = subnet.gateway
        mask = subnet.netmask
        return (gateway, mask)

    def get_all_subnets(self):
        rlt = self.dbmgr.read_record_list({"zone_id": self.zone_id})
        if not rlt.success:
            Log(2, "SubnetMgr.get_all_subnets fail,as[%s]" % (rlt.message))
            return rlt

        subnet_list = []
        for info in rlt.content:
            subnet = Subnet(info[ID], info["ip"], info["netmask_length"], info["router"])
            subnet_list.append(subnet)
        return Result(subnet_list)

    def assign_new_subnet(self, vlan_id):
        res = self.load_data()
        if res == FAIL:
            Log(2, "SubnetMgr.assign_new_subnet load data fail. zone_id = %s" % self.zone_id)
            return Result("", FAIL, "SubnetMgr.assign_new_subnet load data fail.")

        has = False
        for index in range(0, self.sub_net_num):
            if index not in self.__index_store:
                has = True
                break

        if has == False:
            Log(2, "SubnetMgr.assign_new_subnet all subnet is in use.")
            return Result("", FAIL, "SubnetMgr.assign_new_subnet all subnet is in use.")

        offset = 2 ** (32 - self.subnet_mask_lenth) * index
        ip = self.host_index(offset).dq
        # net = Network(ip, self.subnet_mask_lenth)

        info = {}
        info["zone_id"] = self.zone_id
        info["subnet_number"] = index
        info["vlan_id"] = vlan_id
        # info["netmask"] = str(net.netmask().dq)
        info["router"] = self.host_index(offset + 1).dq
        info["netmask_length"] = self.subnet_mask_lenth
        info["ip"] = ip

        rlt = self.dbmgr.create_subnet(info)
        if not rlt.success:
            Log(2, "SubnetMgr.create_new_sunbet for[%s][%s] fail.as[%s]" % (vlan_id, index, rlt.message))
            return rlt

        info[ID] = rlt.content
        subnet = Subnet(info[ID], info["ip"], info["netmask_length"], info["router"])

        return Result(subnet)

    def release_subnet(self, vlan_id):
        rlt = self.get_subnet_by_vlan_id(vlan_id)
        if not rlt.success:
            Log(2, "The subnet[%s] not exist." % (vlan_id))
            return Result(SUCCESS)
        subnet = rlt.content

        rlt = subnet.release()
        if not rlt.success:
            Log(2, "SubnetMgr.release_subnet[%s]fail,as[%s]" % (vlan_id, rlt.message))

        self.dbmgr.del_subnet(subnet.subnet_id)
        return Result(SUCCESS)

