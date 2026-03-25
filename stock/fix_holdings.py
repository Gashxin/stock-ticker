# -*- coding: utf-8 -*-
# Fix holdings data

with open('daily_report_full.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Replace GUOXIN
content = content.replace(
    "'000032': ('深桑达A(国)', 15500, 21.033),",
    "'000032_g': ('深桑达A(国)', 15500, 21.033),"
)

# Replace ZHONGJIN
content = content.replace(
    "'000032': ('深桑达A(中)', 18900, 22.934),",
    "'000032_z': ('深桑达A(中)', 18900, 22.934),"
)
content = content.replace(
    "'002497': ('雅化集团', 100, 412.975),",
    "'002497_z': ('雅化集团(中)', 100, 412.975),"
)
content = content.replace(
    "'002176': ('江特电机', 100, 1657.930),",
    "'002176_z': ('江特电机(中)', 100, 1657.930),"
)

# Replace YAHU_BUY
content = content.replace(
    "'002497': ('雅化集团(买)', 1800, 25.05),",
    "'002497_y': ('雅化集团(买)', 1800, 25.05),"
)

with open('daily_report_full.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed holdings keys')
