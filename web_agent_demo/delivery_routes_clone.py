from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class Point:
    lat: float
    long: float
    x: float
    y: float


@dataclass(frozen=True)
class RouteMeasure:
    unit: str
    value: float


@dataclass(frozen=True)
class RouteData:
    distance: RouteMeasure
    time: RouteMeasure
    pointsEncoded: str


@dataclass(frozen=True)
class SegmentData:
    orderId: str
    index: int
    from_point: Point
    to: Point
    segmentType: Literal["selected", "candidate", "rejected"]
    route: RouteData

    def to_web(self) -> dict[str, object]:
        data = asdict(self)
        data["from"] = data.pop("from_point")
        return data


@dataclass(frozen=True)
class DeliveryJobData:
    Id: str
    carNo: int
    deliveryTimeGroup: int
    loadCapacity: int
    maxCapacity: int
    solverJobId: str
    latitude: float
    longitude: float
    createdAt: int
    segments: list[SegmentData]

    def to_web(self) -> dict[str, object]:
        data = asdict(self)
        data["segments"] = [segment.to_web() for segment in self.segments]
        return data


def _point(x: float, y: float) -> Point:
    return Point(lat=37.56 - (y - 50) * 0.0022, long=126.96 + (x - 50) * 0.0032, x=x, y=y)


def _route(distance_km: float, minutes: float) -> RouteData:
    return RouteData(
        distance=RouteMeasure(unit="km", value=distance_km),
        time=RouteMeasure(unit="minutes", value=minutes),
        pointsEncoded="",
    )


def autosolver_delivery_job() -> DeliveryJobData:
    segments = [
        SegmentData("T0023", 0, _point(66, 18), _point(52, 22), "candidate", _route(2.8, 6)),
        SegmentData("T0018", 1, _point(52, 22), _point(72, 48), "selected", _route(5.1, 12)),
        SegmentData("T0012", 2, _point(72, 48), _point(34, 52), "selected", _route(6.4, 14)),
        SegmentData("T0038", 3, _point(34, 52), _point(40, 78), "selected", _route(4.3, 11)),
        SegmentData("T0029", 4, _point(58, 56), _point(84, 70), "candidate", _route(7.2, 17)),
        SegmentData("T0049", 5, _point(66, 18), _point(82, 25), "rejected", _route(8.6, 24)),
    ]
    return DeliveryJobData(
        Id="delivery-job-autosolver-001",
        carNo=17,
        deliveryTimeGroup=2,
        loadCapacity=6,
        maxCapacity=9,
        solverJobId="autosolver-route-source",
        latitude=segments[0].from_point.lat,
        longitude=segments[0].from_point.long,
        createdAt=0,
        segments=segments,
    )


def autosolver_map_entities() -> dict[str, object]:
    return {
        "warehouse": {"id": "D01", "label": "Warehouse D01", **asdict(_point(14, 18))},
        "merchants": [{"id": "R01", "label": "商家 R01", **asdict(_point(66, 18))}],
        "vehicles": [
            {"id": "C017", "label": "骑手 C017", "capacity": 3, **asdict(_point(45, 34))},
            {"id": "C035", "label": "骑手 C035", "capacity": 3, **asdict(_point(58, 56))},
            {"id": "C049", "label": "骑手 C049", "capacity": 2, **asdict(_point(82, 25))},
        ],
        "customers": [
            {"id": "T0012", "label": "订单 T0012", "timeGroup": "11:42", **asdict(_point(34, 52))},
            {"id": "T0018", "label": "订单 T0018", "timeGroup": "11:58", **asdict(_point(72, 48))},
            {"id": "T0023", "label": "订单 T0023", "timeGroup": "12:12", **asdict(_point(52, 22))},
            {"id": "T0029", "label": "订单 T0029", "timeGroup": "12:36", **asdict(_point(84, 70))},
            {"id": "T0038", "label": "订单 T0038", "timeGroup": "12:48", **asdict(_point(40, 78))},
        ],
    }


def route_feature_collection(stage: str = "final") -> dict[str, object]:
    features = []
    for segment in autosolver_delivery_job().segments:
        if stage == "pending":
            continue
        if stage == "running" and segment.segmentType == "selected":
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "orderId": segment.orderId,
                    "segmentType": segment.segmentType,
                    "distance": segment.route.distance.value,
                    "time": segment.route.time.value,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [segment.from_point.long, segment.from_point.lat],
                        [segment.to.long, segment.to.lat],
                    ],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def autosolver_map_payload(stage: str = "final") -> dict[str, object]:
    return {
        "entities": autosolver_map_entities(),
        "deliveryJob": autosolver_delivery_job().to_web(),
        "routeSource": route_feature_collection(stage),
        "layers": [
            {"id": "candidate-route-layer", "type": "line", "source": "delivery-route-source"},
            {"id": "selected-route-layer", "type": "line", "source": "delivery-route-source"},
        ],
    }
