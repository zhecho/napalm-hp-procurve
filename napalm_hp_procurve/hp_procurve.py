"""
Napalm driver for HpProcurve Devices
Read https://napalm.readthedocs.io for more information.
"""
from netmiko import ConnectHandler, FileTransfer, InLineTransfer
from netmiko import __version__ as netmiko_version

import sys
import re
import logging
from json import dumps

from napalm.base.utils import py23_compat
from napalm.base.base import NetworkDriver
from napalm.base.exceptions import (
    ConnectionException,
    SessionLockedException,
    MergeConfigException,
    ReplaceConfigException,
    CommandErrorException,
    )
from napalm.base.helpers import (
    textfsm_extractor,
)
logger = logging.getLogger(__name__)


class HpProcurvePrivilegeError(Exception):
    pass

class HpMacFormatError(Exception):
    pass

class HpNoMacFound(Exception):
    pass

class HpProcurveDriver(NetworkDriver):
    """ Napalm driver for HpProcurve devices.  """
    _MINUTE_SECONDS = 60
    _HOUR_SECONDS = 60 * _MINUTE_SECONDS
    _DAY_SECONDS = 24 * _HOUR_SECONDS
    _WEEK_SECONDS = 7 * _DAY_SECONDS
    _YEAR_SECONDS = 365 * _DAY_SECONDS

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """ Constructor.
        
        Additional Optional args:
            - proxy_host - SSH hopping station 
            - proxy_username - hopping station username
            - proxy_password - hopping station password
            - proxy_port - hopping station ssh port
            TODO: 
                Set proxy host to work with user/password 
                (works only with preloaded ssh-key in the ssh-agent for now)
        """

        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        if optional_args is None:
            optional_args = {}

        # proxy part
        self.proxy_host = optional_args.get('proxy_host', None)
        self.proxy_username = optional_args.get('proxy_username', None)
        self.proxy_password = optional_args.get('proxy_password', None)
        self.proxy_port = optional_args.get('proxy_port', None)
       

        # Check for proxy parameters and generate ssh config file
        if self.proxy_host:
            if self.proxy_port and self.proxy_username: 
                print("Generate SSH proxy config file for hopping station: {}".format(self.proxy_host))
                self.ssh_proxy_file = self._generate_ssh_proxy_file()
            else:
                raise ValueError("All proxy options must be specified ")
        else:
            self.ssh_proxy_file = None

        # Netmiko possible arguments
        netmiko_argument_map = {
            'ip': None,
            'username': None,
            'password': None,
            'port': None,
            'secret': '',
            'verbose': False,
            'keepalive': 30,
            'global_delay_factor': 2,
            'use_keys': False,
            'key_file': None,
            'ssh_strict': False,
            'system_host_keys': False,
            'alt_host_keys': False,
            'alt_key_file': '',
            'ssh_config_file': None,
        }
         

        fields = netmiko_version.split('.')
        fields = [int(x) for x in fields]
        maj_ver, min_ver, bug_fix = fields
        if maj_ver >= 2:
            netmiko_argument_map['allow_agent'] = False
        elif maj_ver == 1 and min_ver >= 1:
            netmiko_argument_map['allow_agent'] = False

        # Build dict of any optional Netmiko args
        self.netmiko_optional_args = {}
        for k, v in netmiko_argument_map.items():
            try:
                self.netmiko_optional_args[k] = optional_args[k]
            except KeyError:
                pass
        if self.ssh_proxy_file:
            self.netmiko_optional_args['ssh_config_file'] = self.ssh_proxy_file

    
    def _generate_ssh_proxy_file(self):
        filename = '/var/tmp/ssh_proxy_'+ self.hostname
        fh = open(filename, 'w')
        fh.write('Host '+ self.hostname + '\n')
        fh.write('HostName '+ self.hostname + '\n')
        fh.write('User '+ self.proxy_username +'\n')
        fh.write('Port 22'+'\n')
        fh.write('StrictHostKeyChecking no\n')
        fh.write('ProxyCommand ssh '
                + self.proxy_username  +'@'+ self.proxy_host+' nc %h %p')
        fh.close()
        return filename

 
    def open(self):
        """Open a connection to the device."""
        self.device = ConnectHandler(
                device_type = 'hp_procurve',
                host = self.hostname,
                username = self.username,
                password = self.password,
                **self.netmiko_optional_args)
        """ Get current privilege """
        self.get_current_privilege()

    def close(self):
        """Close the connection to the device."""
        self.device.disconnect()

    def _send_command(self, command):
        """ Wrapper for self.device.send.command().
        If command is a list will iterate through commands until valid command.
        """
        try:
            if isinstance(command, list):
                for cmd in command:
                    output = self.device.send_command(cmd)
                    if "% Unrecognized" not in output:
                        break
            else:
                # TODO: Why send_command_timing() works and send_command()
                # doesn't 
                # output = self.device.send_command(command)
                output = self.device.send_command_timing(command)
            return output
        except (socket.error, EOFError) as e:
            raise ConnectionClosedException(str(e))

    def get_current_privilege(self):
        """ Get current privilege 
            "show telnet" output depends on os_version of the device !!!@#!@#!#$
        """
        raw_out = self.device.send_command_timing('show telnet', delay_factor=2)
        dev_version = self.get_version()
        if dev_version.startswith(('K.','YA.','WC.')):
            show_telnet_entries = textfsm_extractor(self, "show_telnet_vK", raw_out)
        else:
            show_telnet_entries = textfsm_extractor(self, "show_telnet", raw_out)
        for row in show_telnet_entries:
            if row['session'].startswith('**'): 
                self.current_user_level = row['user_level']
        return self.current_user_level

    def privilege_escalation(self, os_version=''):
        """ Check userlevel mode with command 'show telnet '
        Procurve Privilege levels: Operator, Manager, Superuser
        
        ProCurve-J8770A-Switch-4204vl> show telnet                                    
                                                                 
         Telnet Activity                                                 
                                                                         
          Session Privilege From            To                           
          ------- --------- --------------- ---------------              
                1 Superuser Console                                      
            **  2 Operator    192.xxx.xxx.xxx
                                                                 
        ProCurve-J8770A-Switch-4204vl> show telnet                                    
                                                                        
         Telnet Activity                                                        
                                                                                
          Session Privilege From            To                                  
          ------- --------- --------------- ---------------                     
                1 Superuser Console                                             
            **  2 Manager     192.xxx.xxx.xxx
       
        """
        os_version = os_version

        if self.current_user_level.lower() == 'manager': 
            msg = f' Already in user privilege level: {self.current_user_level}'
            logger.info(msg); print(msg)
            return 0
        elif self.current_user_level.lower() in ['operator' ]: 
            # Escalate user level in order to have all commands available
            # if os_version:
                # os_version = os_version
            # else:
                # os_version = self.get_version()['os_version']
            cmd = 'enable'
            l1_password = self.device.password
            l2_password = self.device.secret
            self.device.send_command_expect(cmd, expect_string='sername:')
            self.device.send_command_expect(self.username, expect_string='assword:')
            self.device.send_command_timing(l2_password, strip_command=True)
            # Check and confirm user level mode
            self.get_current_privilege()
            if self.current_user_level.lower() == 'manager': 
                msg = f' --- Changed to user level: {self.current_user_level} ---' 
                logger.info(msg); print(msg)
                return 0
            else:
                raise HpProcurvePrivilegeError


    def get_mac_address_table(self, raw_mac_table=None):

        """
        Returns a lists of dictionaries. Each dictionary represents an entry in the MAC Address
        Table, having the following keys:
            * mac (string)
            * interface (string)
            * vlan (int)
            * active (boolean)
            * static (boolean)
            * moves (int)
            * last_move (float)

        However, please note that not all vendors provide all these details.
        E.g.: field last_move is not available on JUNOS devices etc.

        Example::

            [
                {
                    'mac'       : '00:1C:58:29:4A:71',
                    'interface' : 'Ethernet47',
                    'vlan'      : 100,
                    'static'    : False,
                    'active'    : True,
                    'moves'     : 1,
                    'last_move' : 1454417742.58
                },
                {
                    'mac'       : '00:1C:58:29:4A:C1',
                    'interface' : 'xe-1/0/1',
                    'vlan'       : 100,
                    'moves'     : 2,
                    'last_move' : 1453191948.11
                },
                {
                    'mac'       : '00:1C:58:29:4A:C2',
                    'interface' : 'ae7.900',
                    'vlan'      : 900,
                    'static'    : False,
                    'active'    : True,
                    'moves'     : None,
                    'last_move' : None
                }
            ]
        """
        if raw_mac_table is not None:
            if 'No mac address found' in raw_mac_table:
                return ['No mac address found']
            out_mac_table = raw_mac_table
        else:
            # Disable Pageing of the device
            self.disable_pageing()
        raw_out = self._send_command('show mac-address')
        dev_version = self.get_version()
        if dev_version.startswith('K.'):
            mac_table_entries = textfsm_extractor(self, "show_mac_address_all_vK", raw_out)
        else: 
            mac_table_entries = textfsm_extractor(self, "show_mac_address_all", raw_out)
        # owerwrite some values in order to be compliant 
        for row in mac_table_entries:                                            
            row['mac'] = self.format_mac_cisco_way(row['mac'])                   
            row['interface'] = self.normalize_port_name(row['interface'])        
        return mac_table_entries


    def normalize_port_name(self,res_port):
        """ Convert Short HP interface names to long (ex: BAGG519 --> Bridge-Aggregation 519)"""
        raise NotImplementedError
        # if re.match('^BAGG\d+',res_port):
        #     # format port BAGG519 --> Bridge-Aggregation 519
        #     agg_port_name = res_port.replace('BAGG','Bridge-Aggregation ')
        #     return agg_port_name
        # elif re.match('^Bridge-Aggregation\d*',res_port):
        #     agg_port_name = res_port
        #     return agg_port_name
        # elif re.match('^XGE\d.*',res_port):
        #     # format port XGE1/2/0/7 --> Ten-GigabitEthernet 1/2/0/7
        #     port_name = res_port.replace('XGE','Ten-GigabitEthernet ')
        #     # print(" --- Port Name: "+'\x1b[1;32;40m' +"{}" .format(port_name)+'\x1b[0m')
        #     return port_name
        # elif re.match('^GE\d.*',res_port):
        #     # format port GE1/5/0/19 --> GigabitEthernet 1/5/0/19
        #     port_name = res_port.replace('GE','GigabitEthernet ')
        #     # print(" --- Port Name: "+'\x1b[1;32;40m' +"{}" .format(port_name)+'\x1b[0m')
        #     return port_name
        # elif re.match('^Vlan\d+',res_port):
        #     # format port Vlan4003 --> Vlan-interface4003
        #     port_name = res_port.replace('Vlan','Vlan-interface')
        #     # print(" --- Port Name: "+'\x1b[1;32;40m' +"{}" .format(port_name)+'\x1b[0m')
        #     return port_name
        # else:
        #     return res_port 
        #     # print('\x1b[1;31;40m' + " --- Unknown Port Name: {} --- ".format(res_port)+'\x1b[0m')


    
    def get_active_physical_ports(self, aggregation_port):
        """ Return textFSM table with physical ports joined as "aggregation_port" """
        from IPython import embed; embed()
        from IPython.core import debugger; debug = debugger.Pdb().set_trace; debug()
        raw_out = self._send_command('display link-aggregation verbose ' + str(aggregation_port))
        port_entries = textfsm_extractor(self, "display_link_aggregation_verbose", raw_out)
        a_ports = list()
        for row in port_entries:
            # Return only active ports
            if row['status'].lower() == 's':
                a_ports.append(self.normalize_port_name(row['port_name']))
        
        if a_ports:
            print(f' --- Active ports of the aggregation_port {aggregation_port} ---')
            print(dumps(a_ports, sort_keys=True, indent=4, separators=(',', ': ')))
            return a_ports
        else:
            raise HpNoActiePortsInAggregation

    def trace_mac_address(self, mac_address):
        """ Search for mac_address, get switch port and return lldp/cdp
        neighbour of that port """
        result = { 
                'found': False,
                'cdp_answer': False,
                'lldp_answer': False,
                'local_port': '',
                'remote_port': '',
                'next_device': '',
                'next_device_descr': '',
                }
        try:
            self.privilege_escalation()
            self.disable_pageing()
            mac_address = self.hp_mac_format(mac_address)
            raw_out = self._send_command('show mac-address ' + mac_address)
            dev_version = self.get_version()
            if dev_version.startswith('K.'):
                mac_address_entries = textfsm_extractor(self, "show_mac_address_vK", raw_out)
            else: 
                mac_address_entries = textfsm_extractor(self, "show_mac_address", raw_out)
            if ' not found.' in raw_out or len(mac_address_entries) == 0:
                raise HpNoMacFound
            else:
                msg = f' --- Found {mac_address} mac address --- \n'
                print(msg); logger.info(msg)
                result['found'] = True
            # print(dumps(mac_address_entries, sort_keys=True, indent=4, separators=(',', ': ')))

            port = mac_address_entries[0]['port']
            # check if port is aggregated
            if port.startswith('Trk'):
                port = self.get_active_physical_ports(port)[0]

            result['local_port'] = port
            show_lldp_entries = self.get_lldp_neighbors_detail(interface=port)
            if show_lldp_entries:
                result['lldp_answer'] = True
                result['next_device'] = show_lldp_entries[0]['system_name']
                result['next_device_descr'] = show_lldp_entries[0]['system_description']
                msg = f' --- Neighbour System Name: {result["next_device"]}'
                msg += f'\n --- Neighbor System Description: {show_lldp_entries[0]["system_description"]}'
                print(msg); logger.info(msg)
            return result
        except HpMacFormatError as e:
            msg = f'Unrecognised Mac format: {mac_address}'
            logger.error(msg)
            print(msg)
            return result
        except HpNoMacFound as e:
            msg = f' --- No mac address {mac_address} found: {e} ---'
            print(msg)
            logger.info(msg)
            return result
        except Exception as e:
            raise e

    def hp_mac_format(self, mac):
        """ return hp mac format """
        if ':' in mac:
            # 04:4b:ed:31:75:cd -> 044bed3175cd
            temp_mac = "".join(mac.split(':'))
        elif '-' in mac:
            # 04-4b-ed-31-75-cd -> 044bed3175cd
            # 044b-ed31-75cd -> 044bed3175cd
            temp_mac = "".join(mac.split('-'))
        else:
            # match '044bed3175cd'
            m = re.match(r'.*([a-f,A-F,0-9]{12})', mac)
            if m:
                temp_mac = mac
            else:
                raise HpMacFormatError(f'Unrecognised Mac format: {mac}')
        out_mac = ''
        for idx, value in enumerate(temp_mac):
            if idx in [4,8]:
                out_mac += '-'
            out_mac += value
        return str(out_mac)

    def disable_pageing(self):
        """ Disable pageing on the device is might be blocked by AAA server so
        check privilege level before this """
        try:
            if self.current_user_level.lower() == 'manager':
                out_disable_pageing = self.device.send_command('no page')
            else:
                self.privilege_escalation()
        except Exception as e:
            print("Disable Pageing cli command error: {}".format(out_disable_pageing))
            raise e

    def get_version(self):
        """ Return procurve version, vendor, model and uptime.  """
        raw_out = self._send_command('show version')
        version_entries = textfsm_extractor(self, "show_version", raw_out)
        version = version_entries[0]['os_version']
        return str(version)


    def get_lldp_neighbors_detail(self, interface=""):
        """ Get lldp neighbor details 
        return textfsm table with the following row:
        {
            local_port
            chassis_type
            chassis_id
            port_type
            port_id
            system_name
            system_description
            port_description
            system_capabilities_supported
            system_capabilities_enabled
            remote_mgmt_ip_family
            remote_mgmt_ip
        }
        """
        raw_lldp_out = self._send_command('show lldp info remote-device ' + interface)
        show_lldp_entries = textfsm_extractor(self, "show_lldp_info_remote_device", raw_lldp_out)
        print(f' --- LLDP neighbour info ---\n')
        print(dumps(show_lldp_entries, sort_keys=True, indent=4, separators=(',', ': ')))
        if len(show_lldp_entries) == 0:
            return {}
        return show_lldp_entries

    def get_cdp_neighbors_detail(self, interface=""):
        """ cdp cli commands depends on comware version """
        # TODO  not implemented 
        return False

    def format_mac_cisco_way(self, macAddress):
        """ format mac address with ":" AA:BB:CC:DD:EE:FF """
        macAddress = macAddress.replace('-','')
        return macAddress[:2] +\
                ':'+macAddress[2:4]+\
                ':'+macAddress[4:6]+\
                ':'+macAddress[6:8]+\
                ':'+macAddress[8:10]+\
                ':'+macAddress[10:12]


