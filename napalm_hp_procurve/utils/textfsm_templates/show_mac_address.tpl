# 
# Procurve "show mac-address xxxx-xxxx"
#
#                                                                    
# Status and Counters - Address Table - d4c9ef-e358ac                
#                                                                    
#  MAC Address : d4c9ef-e358ac                                       
#  Located on Port : C14                                             
#                                                                    
#
Value MAC_ADDRESS (\S+)
Value PORT (\S+)

Start
  ^\s+MAC\s+Address\s+\:\s+${MAC_ADDRESS}
  ^\s+Located\s+on\s+Port\s+\:\s+${PORT} -> Record

EOF
