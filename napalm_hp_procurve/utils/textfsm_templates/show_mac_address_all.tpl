# 
# Procurve version K.xx "show mac-address"
#
#MAC ADDR       VLAN ID  STATE          PORT INDEX               AGING TIME(s)                      
#002347-5babcd  1        Learned        A23                      AGING                              
#002347-5babcd  1        Learned        A23                      AGING                              
#005012-01abcd  1        Learned        Trk1                     AGING                              
#1cdf0f-b4abcd  1        Learned        Trk1                     AGING                              
#1cdf0f-b4abcd  1        Learned        Trk1                     AGING                              
#20677c-9dabcd  1        Learned        E24                      AGING                              
#20677c-9dabcd  1        Learned        E24                      AGING                              
#d07e28-cfabcd  1        Learned        Trk1                     AGING                              
#d07e28-cfabcd  1        Learned        Trk1                     AGING                              
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
Value STATE (\S+)
Value AGING (\S+)

Start
  ^${MAC}\s+${VLAN}\s+${STATE}\s+${INTERFACE}\s+${AGING} -> Record

EOF
