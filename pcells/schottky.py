"""
Schottky - N+/Metal Schottky Diode with Guard Rings

A high-reliability Schottky diode featuring:
- N+/Metal junction with contact array (Nx × Ny)
- Dual Metal2 vias for current distribution
- Four-sided pSD guard rings with lateral ties
- Thermal via network for heat dissipation

Parameters:
    w (float): Junction width in microns (1.0 µm default)
    l (float): Junction length in microns (0.3 µm default)
    Nx (int): Number of columns in array (1-10)
    Ny (int): Number of rows in array (1-10)
    m (str): Multiplier factor for model

Pins: PLUS (anode, Metal2), MINUS (cathode, Metal1), TIE1 (left guard tie), TIE2 (right guard tie)

Layers: Activ, nSD, Cont, Metal1, Metal2, pSD, Via1, SalBlock, NWell, nBuLay, ThickGateOx, PWell, TEXT, Recog
"""

from revedaEditor.common.layoutShapes import layoutPcell, layoutRect, layoutPin
from quantiphy import Quantity


class schottky(layoutPcell):
    """
    Schottky diode with guard ring isolation and thermal via distribution.
    Provides high-speed switching with controlled leakage current.
    """

    def __init__(self):
        super().__init__()
        self.cellName = "schottky"
        self.setParam("w", "1.0u", "Junction width")
        self.setParam("l", "0.3u", "Junction length")
        self.setParam("Nx", 1, "Columns")
        self.setParam("Ny", 1, "Rows")
        self.setParam("m", "1", "Multiplier")

    def __call__(self):
        # Get parameters
        w_um = float(Quantity(self.getParam("w")))
        l_um = float(Quantity(self.getParam("l")))
        Nx = int(self.getParam("Nx"))
        Ny = int(self.getParam("Ny"))

        # Tech parameters (IHP SG13G2)
        nsdbOcont = 0.45  # Contact offset (µm)
        contW = 0.16  # Contact width (µm)
        contS = 0.18  # Contact spacing (µm)
        metWidth = 0.30  # Metal contact width (µm)
        viaW = 0.19  # Via width (µm)
        
        # Via spacing: width-dependent
        viaS = 0.22 if w_um < 1.52 else 0.29
        
        psdWidth = 0.5  # Guard ring p-doped width (µm)
        nwellScont = 0.25  # N-well surround (µm)
        activWidth = 0.3  # Active region width (µm)
        gateOxOpsd = 0.17  # Gate oxide pad (µm)

        # Array pitch (center-to-center spacing)
        pcStepX = l_um + 2.0  # Horizontal pitch (µm)
        pcStepY = w_um + 1.7  # Vertical pitch (µm)

        # Guard ring dimensions
        grdWidth = psdWidth
        nwellSurr = nwellScont

        # --- Main Array Loop ---
        for ny_idx in range(Ny):
            for nx_idx in range(Nx):
                # Position of this junction element
                x_base = nx_idx * pcStepX
                y_base = ny_idx * pcStepY

                # === 1. Active Region (junction area) ===
                cont_x = x_base + nsdbOcont
                cont_y = y_base + nsdbOcont

                # Contact rectangle (N+ area)
                self.shapes.append(
                    layoutRect(
                        layer="Activ",
                        dataType="drawing",
                        x=cont_x,
                        y=cont_y,
                        width=l_um,
                        height=w_um,
                    )
                )

                # === 2. nSD Blocking (prevent unwanted N-doping) ===
                self.shapes.append(
                    layoutRect(
                        layer="nSD",
                        dataType="block",
                        x=cont_x - 0.1,
                        y=cont_y - 0.1,
                        width=l_um + 0.2,
                        height=w_um + 0.2,
                    )
                )

                # === 3. Contact Layer ===
                # Single contact for junction
                self.shapes.append(
                    layoutRect(
                        layer="Cont",
                        dataType="drawing",
                        x=cont_x + (l_um - contW) / 2,
                        y=cont_y + (w_um - contW) / 2,
                        width=contW,
                        height=contW,
                    )
                )

                # === 4. Metal1 Overlay ===
                self.shapes.append(
                    layoutRect(
                        layer="Metal1",
                        dataType="drawing",
                        x=cont_x - 0.05,
                        y=cont_y - 0.05,
                        width=l_um + 0.1,
                        height=w_um + 0.1,
                    )
                )

                # === 5. Dual Via1 (left and right) for current distribution ===
                via_center = cont_x + l_um / 2
                via_spacing = viaS
                
                # Left via
                via_left_x = via_center - via_spacing / 2
                self.shapes.append(
                    layoutRect(
                        layer="Via1",
                        dataType="drawing",
                        x=via_left_x - viaW / 2,
                        y=cont_y,
                        width=viaW,
                        height=w_um,
                    )
                )

                # Right via
                via_right_x = via_center + via_spacing / 2
                self.shapes.append(
                    layoutRect(
                        layer="Via1",
                        dataType="drawing",
                        x=via_right_x - viaW / 2,
                        y=cont_y,
                        width=viaW,
                        height=w_um,
                    )
                )

                # === 6. Metal2 Bus (current collection) ===
                self.shapes.append(
                    layoutRect(
                        layer="Metal2",
                        dataType="drawing",
                        x=cont_x - 0.15,
                        y=cont_y - 0.15,
                        width=l_um + 0.3,
                        height=w_um + 0.3,
                    )
                )

                # === 7. SalBlock (Salicide prevention) ===
                self.shapes.append(
                    layoutRect(
                        layer="SalBlock",
                        dataType="drawing",
                        x=cont_x - 0.2,
                        y=cont_y - 0.2,
                        width=l_um + 0.4,
                        height=w_um + 0.4,
                    )
                )

                # === 8. N-Well Surround ===
                nwell_x = cont_x - nwellSurr
                nwell_y = cont_y - nwellSurr
                nwell_w = l_um + 2 * nwellSurr
                nwell_h = w_um + 2 * nwellSurr

                self.shapes.append(
                    layoutRect(
                        layer="NWell",
                        dataType="drawing",
                        x=nwell_x,
                        y=nwell_y,
                        width=nwell_w,
                        height=nwell_h,
                    )
                )

                # === 9. nBuLay (buried layer marker) ===
                self.shapes.append(
                    layoutRect(
                        layer="nBuLay",
                        dataType="drawing",
                        x=nwell_x,
                        y=nwell_y,
                        width=nwell_w,
                        height=nwell_h,
                    )
                )

                # === 10. ThickGateOx (protection) ===
                self.shapes.append(
                    layoutRect(
                        layer="ThickGateOx",
                        dataType="drawing",
                        x=cont_x - gateOxOpsd,
                        y=cont_y - gateOxOpsd,
                        width=l_um + 2 * gateOxOpsd,
                        height=w_um + 2 * gateOxOpsd,
                    )
                )

        # --- Guard Rings (Four-Sided Perimeter) ---
        # Calculate overall array dimensions
        array_w = Nx * pcStepX
        array_h = Ny * pcStepY

        # Top guard ring (pSD)
        self.shapes.append(
            layoutRect(
                layer="pSD",
                dataType="drawing",
                x=-psdWidth,
                y=array_h - psdWidth - 0.5,
                width=array_w + 2 * psdWidth,
                height=psdWidth,
            )
        )

        # Bottom guard ring (pSD)
        self.shapes.append(
            layoutRect(
                layer="pSD",
                dataType="drawing",
                x=-psdWidth,
                y=-0.5,
                width=array_w + 2 * psdWidth,
                height=psdWidth,
            )
        )

        # Left guard ring (pSD)
        self.shapes.append(
            layoutRect(
                layer="pSD",
                dataType="drawing",
                x=-psdWidth,
                y=-psdWidth - 0.5,
                width=psdWidth,
                height=array_h + 2 * psdWidth + 1.0,
            )
        )

        # Right guard ring (pSD)
        self.shapes.append(
            layoutRect(
                layer="pSD",
                dataType="drawing",
                x=array_w,
                y=-psdWidth - 0.5,
                width=psdWidth,
                height=array_h + 2 * psdWidth + 1.0,
            )
        )

        # --- Interconnect Metalwork ---
        # Horizontal Metal1 rail (MINUS pin)
        self.shapes.append(
            layoutRect(
                layer="Metal1",
                dataType="drawing",
                x=-0.5,
                y=array_h + 0.3,
                width=array_w + 1.0,
                height=0.1,
            )
        )

        # --- Pins ---
        # PLUS pin (Metal2 collection)
        self.shapes.append(
            layoutPin(
                name="PLUS",
                layer="Metal2",
                dataType="pin",
                x=array_w / 2,
                y=array_h / 2,
                width=0.1,
                height=0.1,
            )
        )

        # MINUS pin (Metal1 cathode)
        self.shapes.append(
            layoutPin(
                name="MINUS",
                layer="Metal1",
                dataType="pin",
                x=array_w / 2,
                y=array_h + 0.3,
                width=0.3,
                height=0.1,
            )
        )

        # TIE1 pin (Left guard tie)
        self.shapes.append(
            layoutPin(
                name="TIE1",
                layer="Metal1",
                dataType="pin",
                x=-psdWidth / 2,
                y=array_h / 2,
                width=0.1,
                height=0.1,
            )
        )

        # TIE2 pin (Right guard tie)
        self.shapes.append(
            layoutPin(
                name="TIE2",
                layer="Metal1",
                dataType="pin",
                x=array_w + psdWidth / 2,
                y=array_h / 2,
                width=0.1,
                height=0.1,
            )
        )

        # === Diode Recognition Marker ===
        self.shapes.append(
            layoutRect(
                layer="Recog",
                dataType="diode",
                x=-1.0,
                y=-1.0,
                width=0.1,
                height=0.1,
            )
        )
