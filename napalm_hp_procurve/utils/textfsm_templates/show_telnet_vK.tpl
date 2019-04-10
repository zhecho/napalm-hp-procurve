# 
# Procurve version K.XX "show telnet"
#
# Telnet Activity                                                            
#                                                                            
# Source IP Selection: Outgoing Interface                                    
#                                                                            
# --------------------------------------------------------                   
# Session  :     1                                                           
# Privilege: Manager                                                         
# From     : Console                                                         
# To       :                                                                 
# --------------------------------------------------------                   
# Session  : **  2                                                           
# Privilege: Operator                                                        
# From     : 1.x.x.x
# To       :                                                                 
#
Value SESSION (\d+|\*\*\s+\d+)
Value USER_LEVEL (\S+)
Value FROM (\S+)

Start
  ^\s+Session\s+\:\s+${SESSION}
  ^\s+Privilege\:\s+${USER_LEVEL}
  ^\s+From\s+\:\s+${FROM} -> Record

EOF
