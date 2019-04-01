# 
# Procurve "show lldp info remote-device PORT"
#
# LLDP Remote Device Information Detail                                                    
#                                                                                          
#  Local Port   : B17                                                                      
#  ChassisType  : local                                                                    
#  ChassisId    : CN51G8M1H7                                                               
#  PortType     : local                                                                    
#  PortId       : eth0                                                                     
#  SysName      :                                                                          
#  System Descr : 6.6.8.1-23399HP 560                                                      
#  PortDescr    :                                                                          
#                                                                                          
#  System Capabilities Supported  :                                                        
#  System Capabilities Enabled    :                                                        
#                                                                                          
#  Remote Management Address                                                               
#     Type    : ipv4                                                                       
#     Address : 10.108.3.175                                                               
#                                                                                          
#------------------------------------------------------------------------------            
#  Local Port   : B17                                                                      
#  ChassisType  : mac-address                                                              
#  ChassisId    : d4 c9 ef e3 58 ad                                                        
#  PortType     : mac-address                                                              
#  PortId       : d4 c9 ef e3 58 ad                                                        
#  SysName      : @DE-REM (10.108.3.175)                                                   
#  System Descr : HP AP Controlled,CN51G8M1H7,J9846-60001:65-A,6.6.8.1-23399               
#  PortDescr    : Port 1                                                                   
#                                                                                          
#  System Capabilities Supported  : wlan-access-point                                      
#  System Capabilities Enabled    : wlan-access-point                                      
#                                                                                          
#  Remote Management Address                                                               
#     Type    : ipv4                                                                       
#     Address : 10.108.3.175                                                               
#
Value LOCAL_PORT (\S+)
Value CHASSIS_TYPE (\S+)
Value CHASSIS_ID (.*)
Value PORT_TYPE (\S+)
Value PORT_ID (.*)
Value SYSTEM_NAME (.*)
Value SYSTEM_DESCRIPTION (.*)
Value PORT_DESCRIPTION (.*)
Value SYSTEM_CAPABILITIES_SUPPORTED (\S+)
Value SYSTEM_CAPABILITIES_ENABLED (\S+)
Value REMOTE_MGMT_IP_FAMILY (\S+)
Value REMOTE_MGMT_IP (\d+.\d+.\d+.\d+.)

Start
  ^[-]+ -> REMOTEDEV

REMOTEDEV
  ^\s+Local\s+Port\s+\:\s+${LOCAL_PORT}
  ^\s+ChassisType\s+\:\s+${CHASSIS_TYPE}
  ^\s+ChassisId\s+\:\s+${CHASSIS_ID}
  ^\s+PortType\s+\:\s+${PORT_TYPE}
  ^\s+PortId\s+\:\s+${PORT_ID}
  ^\s+SysName\s+\:\s+${SYSTEM_NAME}
  ^\s+System\s+Descr\s+\:\s+${SYSTEM_DESCRIPTION}
  ^\s+PortDescr\s+\:\s+${PORT_DESCRIPTION}
  ^\s+System\s+Capabilities\s+Supported\s+\:\s+${SYSTEM_CAPABILITIES_SUPPORTED}
  ^\s+System\s+Capabilities\s+Enabled\s+\:\s+${SYSTEM_CAPABILITIES_ENABLED}
  ^\s+Remote\s+Management\s+address
  ^\s+Type\s+\:\s+${REMOTE_MGMT_IP_FAMILY}
  ^\s+Address\s+\:\s+${REMOTE_MGMT_IP} -> Record

EOF
