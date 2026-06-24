from __future__ import annotations

import unittest

from web_agent_demo.day_simulation import (
    DAY_END_S,
    DAY_START_S,
    DaySimulationControls,
    day_world_to_dict,
    generate_full_day_world,
)


class DaySimulationGeneratorTest(unittest.TestCase):
    def test_same_seed_generates_identical_world(self):
        controls = DaySimulationControls(courier_count=36, order_scale=0.82, weather="mixed", congestion_profile="weekday")

        left = day_world_to_dict(generate_full_day_world(seed="stable-day", controls=controls))
        right = day_world_to_dict(generate_full_day_world(seed="stable-day", controls=controls))
        changed = day_world_to_dict(generate_full_day_world(seed="changed-day", controls=controls))

        self.assertEqual(left, right)
        self.assertNotEqual(left["orders"], changed["orders"])
        self.assertEqual(left["summary"]["total_time_slices"], 64)
        self.assertEqual(left["summary"]["total_couriers"], 36)

    def test_default_world_covers_full_day_phases_and_shocks(self):
        world = generate_full_day_world(seed="coverage-day")
        phase_counts = world.summary["phase_counts"]
        shock_counts = world.summary["shock_slice_counts"]

        self.assertEqual(world.time_slices[0].start_s, DAY_START_S)
        self.assertEqual(world.time_slices[-1].end_s, DAY_END_S)
        for phase in ("breakfast", "lunch_peak", "afternoon_tea", "dinner_peak", "night_supply_gap"):
            self.assertGreater(phase_counts.get(phase, 0), 0)
        for shock_type in ("rain_slowdown", "merchant_burst", "road_congestion", "courier_shortage"):
            self.assertGreater(shock_counts.get(shock_type, 0), 0)
        self.assertGreater(world.summary["total_orders"], 300)
        self.assertGreater(world.summary["peak_orders_per_slice"], 12)

    def test_time_slices_reference_valid_orders_and_active_shocks(self):
        world = generate_full_day_world(seed="reference-day")
        order_by_id = {order.id: order for order in world.orders}
        shock_by_id = {shock.id: shock for shock in world.shocks}
        referenced_order_ids = set()

        for time_slice in world.time_slices:
            for order_id in time_slice.order_ids:
                self.assertIn(order_id, order_by_id)
                order = order_by_id[order_id]
                self.assertGreaterEqual(order.created_at_s, time_slice.start_s)
                self.assertLess(order.created_at_s, time_slice.end_s)
                self.assertEqual(order.demand_phase, time_slice.demand_phase)
                self.assertIn(time_slice.demand_phase, order.risk_tags)
                self.assertGreater(order.deadline_s, order.created_at_s)
                referenced_order_ids.add(order_id)
            for shock_id in time_slice.shock_ids:
                shock = shock_by_id[shock_id]
                self.assertLess(shock.start_s, time_slice.end_s)
                self.assertGreater(shock.end_s, time_slice.start_s)
            if time_slice.shock_ids:
                self.assertTrue(time_slice.compare_due)

        self.assertEqual(referenced_order_ids, set(order_by_id))

    def test_controls_scale_order_volume_and_courier_count(self):
        low = generate_full_day_world(
            seed="scale-day",
            controls=DaySimulationControls(courier_count=18, order_scale=0.45, weather="clear", congestion_profile="smooth"),
        )
        high = generate_full_day_world(
            seed="scale-day",
            controls=DaySimulationControls(courier_count=54, order_scale=1.35, weather="storm", congestion_profile="event"),
        )

        self.assertEqual(len(low.couriers), 18)
        self.assertEqual(len(high.couriers), 54)
        self.assertGreater(len(high.orders), len(low.orders) * 2)
        self.assertGreater(high.summary["peak_orders_per_slice"], low.summary["peak_orders_per_slice"])
        self.assertGreater(
            max(item.congestion_level for item in high.time_slices),
            max(item.congestion_level for item in low.time_slices),
        )

    def test_night_courier_shortage_reduces_supply(self):
        world = generate_full_day_world(seed="shortage-day")
        before_shortage = next(item for item in world.time_slices if item.start_s == 20 * 60 * 60 + 45 * 60)
        during_shortage = next(item for item in world.time_slices if item.start_s == 21 * 60 * 60)

        self.assertIn("S-courier-night", during_shortage.shock_ids)
        self.assertLess(during_shortage.courier_supply, before_shortage.courier_supply)
        self.assertGreater(during_shortage.courier_supply, 0)


if __name__ == "__main__":
    unittest.main()
