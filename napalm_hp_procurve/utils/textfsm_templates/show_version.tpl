# 
# Parse comware "show version
# 
#Image stamp:    /sw/code/build/xxx
#                Mar 31 2016 22:48:02                    
#                L.11.45                                 
#                97
#Boot Image:     Primary
Value OS_VERSION (\S+\.\S+\.\S+.*)
Value OS_VERSION_RELEASE (\S+)

Start
  ^Image\s+stamp\:
  ^\s+\S+\s+\S+\s+\S+\s+\S+
  ^\s+${OS_VERSION}
  ^\s+${OS_VERSION_RELEASE}
  ^Boot\s+Image\:\s+\S+ -> Record

EOF
