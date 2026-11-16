"""HWPX 표 구조 확인: python docs/tools/hwpx_inspect.py <file.hwpx>"""

import re
import sys
import zipfile

ROW = re.compile(r'rowCnt="(\d+)"')
COL = re.compile(r'colCnt="(\d+)"')
ADDR = re.compile(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"')
SPAN = re.compile(r'<hp:cellSpan colSpan="(\d+)" rowSpan="(\d+)"')
SIZE = re.compile(r'<hp:cellSz width="(\d+)" height="(\d+)"')
TEXT = re.compile(r"<hp:t>([^<]*)</hp:t>")

x = zipfile.ZipFile(sys.argv[1]).read("Contents/section0.xml").decode("utf-8")
for ti, tbl in enumerate(re.findall(r"<hp:tbl .*?</hp:tbl>", x, re.S)):
    print(f"--- table {ti} rows={ROW.search(tbl).group(1)} cols={COL.search(tbl).group(1)}")
    for tc in re.findall(r"<hp:tc .*?</hp:tc>", tbl, re.S):
        a, sp, sz = ADDR.search(tc), SPAN.search(tc), SIZE.search(tc)
        txt = "".join(TEXT.findall(tc))
        print(f"  r{a.group(2)} c{a.group(1)} span={sp.group(1)}x{sp.group(2)} size={sz.group(1)}x{sz.group(2)} "
              f"paras={tc.count('<hp:p ')} text={txt!r}")
