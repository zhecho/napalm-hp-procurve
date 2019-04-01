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


class HpProcurvePriviledgeError(Exception):
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
        self.current_user_level = self.get_current_priviledge()

    
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

    def close(self):
        """Close the connection to the device."""
        self.device.disconnect()


    def get_current_priviledge(self):
        """ Get current privilege of the user """
        raw_out = self._send_command('show telnet')
        show_telnet_entries = textfsm_extractor(self, "show_telnet", raw_out)
        self.current_user_level = disp_usr_entries[0]['user_level']
        return self.current_user_level

    def priviledge_escalation(self, os_version=''):
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
        
        if self.current_user_level == 'Manager': 
            msg = f' Already in user privilege level: {self.current_user_level}'
            logger.info(msg); print(msg)
            return 0
        elif self.current_user_level in ['Operator' ]: 
            # Escalate user level in order to have all commands available
            if os_version:
                os_version = os_version
            else:
                os_version = self.get_version()['os_version']
            cmd = 'enable'
            l1_password = self.device.password
            l2_password = self.device.secret
            self.device.send_command_expect(cmd, expect_string='sername:')
            self.device.send_command_expect(self.username, expect_string='assword:')
            self.device.send_command_timing(l2_password, strip_command=True)
            # Check and confirm user level mode
            raw_out = self._send_command('show telnet')
            show_telnet_entries = textfsm_extractor(self, "show_telnet", raw_out)
            self.current_user_level = disp_usr_entries[0]['user_level']
            if user_level == 'Manager': 
                msg = f' --- Changed to user level: {user_level} ---' 
                logger.info(msg); print(msg)
                return 0
            else:
                raise HpProcurvePriviledgeError
        


