# 
# Procurve "show mac-address"
#
# Status and Counters - Port Address Table                  
#                                                           
#  MAC Address   Port     VLAN                              
#  ------------- -------- ----                              
#  002347-5abcd A23      1                                 
#  002347-5abcd A23      1                                 
#  005012-0abcd Trk1     1                                 
#  005012-0abcd Trk1     1                                 
#  1cdf0f-babcd Trk1     1                                 
#  1cdf0f-babcd Trk1     1                                 
#  20677c-9abcd E24      1                                 
#  20677c-9abcd E24      1                                 
#  645106-dabcd Trk1     1                                 
#  d07e28-cabcd Trk1     1                                 
#  d07e28-cabcd Trk1     1                                 
#  d07e28-cabcd Trk1     1                                 
# 
# Should return table row like                                                              
#  'mac'       : '00:1C:58:29:4A:C2',
#  'interface' : 'ae7.900',
#  'vlan'      : 900,
#  'static'    : False,
#  'active'    : True,
#  'moves'     : None,
#  'last_move' : None
# 
Value MAC (\S+)
Value INTERFACE (\S+)
Value VLAN (\d+)
Value STATIC (-1)
Value ACTIVE (-1)
Value MOVES (-1)
Value LAST_MOVE (-1)

Start
  ^\s+MAC\s+Address\s+Port\s+VLAN                              
  ^\s+${MAC}\s+${INTERFACE}\s+${VLAN} -> Record

EOF
