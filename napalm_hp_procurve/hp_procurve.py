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
            'global_delay_factor': 3,
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
                output = self.device.send_command(command)
            return output
        except (socket.error, EOFError) as e:
            raise ConnectionClosedException(str(e))

    def get_current_privilege(self):
        """ Get current privilege """
        raw_out = self._send_command('show telnet')
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
        

    def trace_mac_address(self, mac_address):
        """ Search for mac_address, get switch port and return lldp/cdp
        neighbour of that port """
        try:
            self.privilege_escalation()
            self.disable_pageing()
            mac_address = self.hp_mac_format(mac_address)
            raw_out = self._send_command('show mac-address ' + mac_address)
            # raw_table_out = self._send_command('show mac-address')
            if ' not found.' in raw_out:
                raise HpNoMacFound
            mac_address_entries = textfsm_extractor(self, "show_mac_address", raw_out)
            # mac_table = self.get_mac_address_table(raw_mac_table=raw_out)
            msg = f' --- Found mac address --- \n'
            print(msg); logger.info(msg)
            print(dumps(mac_address_entries, sort_keys=True, indent=4, separators=(',', ': ')))
            port = mac_address_entries[0]['port']
            show_lldp_entries = self.get_lldp_neighbors_detail(interface=port)
            msg = f' --- Neighbour System Name: {show_lldp_entries[0]["system_name"]}'
            print(msg); logger.info(msg)
            return show_lldp_entries[0]['system_name'].lower()
        except HpMacFormatError as e:
            msg = f'Unrecognised Mac format: {mac_address}'
            logger.error(msg)
            print(msg)
        except HpNoMacFound as e:
            msg = f' --- No mac address {mac_address} found: {e} ---'
            print(msg)
            logger.info(msg)
            return 'No mac address found'
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
        """ Get lldp neighbor details """
        raw_lldp_out = self._send_command('show lldp info remote-device ' + interface)
        show_lldp_entries = textfsm_extractor(self, "show_lldp_info_remote_device", raw_lldp_out)
        print(dumps(show_lldp_entries, sort_keys=True, indent=4, separators=(',', ': ')))
        return show_lldp_entries

