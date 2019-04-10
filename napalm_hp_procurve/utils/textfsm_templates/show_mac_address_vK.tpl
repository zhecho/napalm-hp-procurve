# 
# Procurve version K.XX "show mac-address xxxx-xxxx"
#
# MAC ADDR       VLAN ID  STATE          PORT INDEX               AGING TIME(s)
# 2c41-3888-ffff 1        Learned        Bridge-Aggregation30     AGING
# a036-9f00-ffff 1        Learned        Bridge-Aggregation30     AGING
# a036-9f00-ffff 1        Learned        Bridge-Aggregation31     AGING
# a036-9f00-ffff 1        Learned        Bridge-Aggregation31     AGING
# b8af-675c-ffff 1        Learned        Bridge-Aggregation2      AGING
# 
#
Value MAC (\S+)
Value INTERFACE (\S+)
Value VLAN (\d+)
Value STATIC (-1)
Value ACTIVE (-1)
Value MOVES (-1)
Value LAST_MOVE (-1)
# other stuff
Value STATE (\S+)
Value AGING (\S+)

Start
  ^MAC\s+ADDR\s+VLAN\s+ID\s+STATE\s+PORT\s+PORT\s+INDEX\s+AGING\s+TIME\(s\)
  ^${MAC}\s+${VLAN}\s+${STATE}\s+${INTERFACE}\s+${AGING} -> Record

EOF
