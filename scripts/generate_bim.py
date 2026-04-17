"""
BIMGenerator — IFC 4 file builder for ArchiText.

All internal geometry is in MILLIMETRES (standard for IFC architecture).
Public API accepts metres and converts internally.

Each room is represented as:
  - IfcSpace  (volume / area tag, shown as 2D fill in plan views)
  - 4 x IfcWall (physical 3D geometry visible in all BIM viewers)
"""

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid
import numpy as np


WALL_THICKNESS = 200.0  # mm (0.2 m)


class BIMGenerator:
    CEILING_HEIGHT = 2.7  # metres (converted to mm internally)

    def __init__(self):
        self.ifc     = ifcopenshell.file(schema="IFC4")
        self.storey  = None
        self._body   = None
        self._spaces = []

        self._project = ifcopenshell.api.run(
            "root.create_entity", self.ifc, ifc_class="IfcProject", name="ArchiText Project"
        )
        ifcopenshell.api.run("unit.assign_unit", self.ifc)

        ctx        = ifcopenshell.api.run("context.add_context", self.ifc, context_type="Model")
        self._body = ifcopenshell.api.run(
            "context.add_context", self.ifc,
            context_type="Model", context_identifier="Body",
            target_view="MODEL_VIEW", parent=ctx,
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _place(self, product, x_mm=0.0, y_mm=0.0, z_mm=0.0):
        matrix = np.eye(4)
        matrix[0][3] = x_mm
        matrix[1][3] = y_mm
        matrix[2][3] = z_mm
        ifcopenshell.api.run(
            "geometry.edit_object_placement", self.ifc,
            product=product, matrix=matrix, is_si=False,
        )

    def _make_wall(self, name, x_mm, y_mm, length_mm, along_x: bool, height_mm: float):
        """Create one IfcWall as a rectangular extruded solid in mm."""
        wall = ifcopenshell.api.run(
            "root.create_entity", self.ifc, ifc_class="IfcWall", name=name
        )
        wall.PredefinedType = "SOLIDWALL"
        self._place(wall, x_mm=x_mm, y_mm=y_mm)

        self.ifc.createIfcRelContainedInSpatialStructure(
            ifcopenshell.guid.new(), None, None, None,
            [wall], self.storey,
        )

        # Wall footprint: length along its local X axis, WALL_THICKNESS along local Y
        if along_x:
            w_len = length_mm
            w_wid = WALL_THICKNESS
        else:
            w_len = WALL_THICKNESS
            w_wid = length_mm

        corners = [
            (0.0,   0.0,   0.0),
            (w_len, 0.0,   0.0),
            (w_len, w_wid, 0.0),
            (0.0,   w_wid, 0.0),
            (0.0,   0.0,   0.0),
        ]
        polyline = self.ifc.createIfcPolyline(
            [self.ifc.createIfcCartesianPoint(pt) for pt in corners]
        )
        profile = self.ifc.createIfcArbitraryClosedProfileDef("AREA", None, polyline)

        axis_pl = self.ifc.createIfcAxis2Placement3D(
            self.ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
            self.ifc.createIfcDirection((0.0, 0.0, 1.0)),
            self.ifc.createIfcDirection((1.0, 0.0, 0.0)),
        )
        solid = self.ifc.createIfcExtrudedAreaSolid(
            profile, axis_pl,
            self.ifc.createIfcDirection((0.0, 0.0, 1.0)),
            height_mm,
        )

        shape_rep = self.ifc.createIfcShapeRepresentation(
            self._body, "Body", "SweptSolid", [solid]
        )
        wall.Representation = self.ifc.createIfcProductDefinitionShape(
            None, None, [shape_rep]
        )
        return wall

    # ── public API ─────────────────────────────────────────────────────────────

    def create_project_structure(self, project_name: str) -> None:
        self._project.Name = project_name

        site   = ifcopenshell.api.run("root.create_entity", self.ifc, ifc_class="IfcSite",           name="Site")
        bldg   = ifcopenshell.api.run("root.create_entity", self.ifc, ifc_class="IfcBuilding",        name=project_name)
        storey = ifcopenshell.api.run("root.create_entity", self.ifc, ifc_class="IfcBuildingStorey",  name="Ground Floor")

        self._place(site)
        self._place(bldg)
        self._place(storey)

        ifcopenshell.api.run("aggregate.assign_object", self.ifc, relating_object=self._project, products=[site])
        ifcopenshell.api.run("aggregate.assign_object", self.ifc, relating_object=site,          products=[bldg])
        ifcopenshell.api.run("aggregate.assign_object", self.ifc, relating_object=bldg,          products=[storey])

        self.storey = storey

    def create_simple_room(
        self,
        name:     str,
        length:   float,   # metres (room footprint X)
        width:    float,   # metres (room footprint Y)
        height:   float = CEILING_HEIGHT,  # metres
        x_offset: float = 0.0,  # metres
        y_offset: float = 0.0,  # metres
    ) -> "ifcopenshell.entity_instance":
        if self.storey is None:
            raise RuntimeError("Call create_project_structure() first.")

        L  = max(float(length),   0.1) * 1000   # mm
        W  = max(float(width),    0.1) * 1000
        H  = max(float(height),   0.1) * 1000
        X  = float(x_offset) * 1000
        Y  = float(y_offset) * 1000
        T  = WALL_THICKNESS

        # ── IfcSpace (plan-view area tag) ──────────────────────────────────────
        space = ifcopenshell.api.run(
            "root.create_entity", self.ifc, ifc_class="IfcSpace", name=name
        )
        space.PredefinedType = "INTERNAL"
        self._place(space, x_mm=X, y_mm=Y)

        self.ifc.createIfcRelContainedInSpatialStructure(
            ifcopenshell.guid.new(), None, None, None,
            [space], self.storey,
        )

        corners = [
            (0.0, 0.0, 0.0), (L, 0.0, 0.0),
            (L,   W,   0.0), (0.0, W, 0.0),
            (0.0, 0.0, 0.0),
        ]
        polyline = self.ifc.createIfcPolyline(
            [self.ifc.createIfcCartesianPoint(pt) for pt in corners]
        )
        profile = self.ifc.createIfcArbitraryClosedProfileDef("AREA", None, polyline)
        axis_pl = self.ifc.createIfcAxis2Placement3D(
            self.ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
            self.ifc.createIfcDirection((0.0, 0.0, 1.0)),
            self.ifc.createIfcDirection((1.0, 0.0, 0.0)),
        )
        solid = self.ifc.createIfcExtrudedAreaSolid(
            profile, axis_pl,
            self.ifc.createIfcDirection((0.0, 0.0, 1.0)),
            H,
        )
        shape_rep = self.ifc.createIfcShapeRepresentation(self._body, "Body", "SweptSolid", [solid])
        space.Representation = self.ifc.createIfcProductDefinitionShape(None, None, [shape_rep])

        # ── 4 IfcWalls (3D geometry visible in all BIM viewers) ───────────────
        # Bottom wall: along X at Y=0
        self._make_wall(f"{name} - South Wall", X,       Y,       L, along_x=True,  height_mm=H)
        # Top wall: along X at Y=W
        self._make_wall(f"{name} - North Wall", X,       Y + W,   L, along_x=True,  height_mm=H)
        # Left wall: along Y at X=0
        self._make_wall(f"{name} - West Wall",  X,       Y,       W + T, along_x=False, height_mm=H)
        # Right wall: along Y at X=L
        self._make_wall(f"{name} - East Wall",  X + L,   Y,       W + T, along_x=False, height_mm=H)

        self._spaces.append(space)
        return space

    @property
    def room_count(self) -> int:
        return len(self._spaces)
