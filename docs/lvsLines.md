# LVS Types for Devices
All 37 symbol.json files under `sg13g2_pr` now have `lvsNetlistLine` and `lvsDeviceType` attributes. Here's a summary of the device types assigned:

| Device Type | Files |
|-------------|-------|
| **mos** | sg13_lv_nmos, sg13_lv_pmos, sg13_lv_rf_nmos, sg13_lv_rf_pmos, sg13_hv_nmos, sg13_hv_pmos, sg13_hv_rf_nmos, sg13_hv_rf_pmos, nmoscl_2, nmoscl_4 |
| **res** | rsil, rhigh, rppd, ntap1, ptap1 |
| **cap** | cap_cmim, cap_rfcmim |
| **dio** | diodevdd_2kv, diodevdd_4kv, diodevss_2kv, diodevss_4kv, idiodevdd_2kv, idiodevdd_4kv, idiodevss_2kv, idiodevss_4kv, dantenna, dpantenna, sg13_svaricap |
| **bjt** | npn13G2, npn13G2_5t, npn13G2l, npn13G2l_5t, npn13G2v, npn13G2v_5t, pnpMPA |
| **subckt** | bondpad, sub |

The LVS netlist lines follow the pattern:
- MOSFETs: `M@instName %pinOrder @cellName w=@w l=@l ...`
- Resistors: `R@instName %pinOrder @cellName w=@w l=@l ...`
- Capacitors: `C@instName %pinOrder @cellName w=@w l=@l ...`
- Diodes: `D@instName %pinOrder @cellName ...`
- BJTs: `Q@instName %pinOrder @cellName ...`
- Subcircuits: `X@instName %pinOrder @cellName`