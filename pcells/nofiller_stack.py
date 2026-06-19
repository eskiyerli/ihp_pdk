"""
NoFillerStack - DRC filler exclusion marker cell

This cell creates rectangular "no-fill" markers on selected metal/active layers.
Used to prevent automatic filler insertion in specified layers. Each layer
rectangle spans the full cell dimensions (w x l).

Parameters:
    w (float): Cell width in microns
    l (float): Cell length in microns
    noAct, noGP, noM1-5, noTM1-2 (bool): Layer control flags

Pins: None (marker cell)

Layers:
    - Activ (nofill datatype)
    - GatPoly (nofill datatype)
    - Metal1-5 (nofill datatype)
    - TopMetal1-2 (nofill datatype)
"""

from revedaEditor.common.layoutShapes import layoutPcell, layoutRect
from quantiphy import Quantity


class NoFillerStack(layoutPcell):
    """
    DRC filler exclusion marker cell with per-layer control.
    Creates rectangular markers to prevent automatic fill operations.
    """

    def __init__(self):
        super().__init__()
        self.cellName = "NoFillerStack"
        self.setParam("w", "10u", "Width")
        self.setParam("l", "10u", "Length")
        self.setParam("noAct", True, "Exclude Activ")
        self.setParam("noGP", True, "Exclude GatPoly")
        self.setParam("noM1", True, "Exclude Metal1")
        self.setParam("noM2", True, "Exclude Metal2")
        self.setParam("noM3", True, "Exclude Metal3")
        self.setParam("noM4", True, "Exclude Metal4")
        self.setParam("noM5", True, "Exclude Metal5")
        self.setParam("noTM1", True, "Exclude TopMetal1")
        self.setParam("noTM2", True, "Exclude TopMetal2")

    def __call__(self):
        # Get parameters
        w = float(Quantity(self.getParam("w")))
        l = float(Quantity(self.getParam("l")))
        noAct = self.getParam("noAct")
        noGP = self.getParam("noGP")
        noM1 = self.getParam("noM1")
        noM2 = self.getParam("noM2")
        noM3 = self.getParam("noM3")
        noM4 = self.getParam("noM4")
        noM5 = self.getParam("noM5")
        noTM1 = self.getParam("noTM1")
        noTM2 = self.getParam("noTM2")

        # Convert to layout coordinates (microns to DBU)
        W = w
        L = l

        # Create nofill rectangles for each enabled layer
        if noAct:
            self.shapes.append(
                layoutRect(
                    layer="Activ",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noGP:
            self.shapes.append(
                layoutRect(
                    layer="GatPoly",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noM1:
            self.shapes.append(
                layoutRect(
                    layer="Metal1",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noM2:
            self.shapes.append(
                layoutRect(
                    layer="Metal2",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noM3:
            self.shapes.append(
                layoutRect(
                    layer="Metal3",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noM4:
            self.shapes.append(
                layoutRect(
                    layer="Metal4",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noM5:
            self.shapes.append(
                layoutRect(
                    layer="Metal5",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noTM1:
            self.shapes.append(
                layoutRect(
                    layer="TopMetal1",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )

        if noTM2:
            self.shapes.append(
                layoutRect(
                    layer="TopMetal2",
                    dataType="nofill",
                    x=0,
                    y=0,
                    width=W,
                    height=L,
                )
            )
