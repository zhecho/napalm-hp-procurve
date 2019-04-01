# 
# Procurve "show telnet"
#
#
# Telnet Activity
#
#  Session Privilege From            To
#  ------- --------- --------------- ---------------
#        1 Superuser Console
#    **  2 Operator    1x.x.x.x
#
Value SESSION (\d+|\*\*\s+\d+)
Value USER_LEVEL (\S+)
Value FROM (\S+)

Start
  ^\s+Session\s+Privilege\s+From\s+To
  ^\s+---
  ^\s+${SESSION}\s+${USER_LEVEL}\s+${FROM} -> Record

EOF
